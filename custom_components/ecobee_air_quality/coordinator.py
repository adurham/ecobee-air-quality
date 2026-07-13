"""Data update coordinator for Ecobee Air Quality."""

from __future__ import annotations

import json
import logging
import time

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .auth import AuthError, async_refresh_token
from .const import ECOBEE_API, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EcobeeAirQualityCoordinator(DataUpdateCoordinator):
    """Coordinator to poll ecobee air quality data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Ecobee Air Quality",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self._access_token: str | None = None
        self._access_token_expires: float = 0
        self._refresh_token: str = entry.data["refresh_token"]

    async def _ensure_token(self, session: ClientSession) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        now = time.time()
        if self._access_token and now < (self._access_token_expires - 300):
            return self._access_token

        try:
            access_token, new_refresh, expires_in = await async_refresh_token(
                session, self._refresh_token
            )
        except AuthError as err:
            raise ConfigEntryAuthFailed(
                "Authentication failed. Please re-authenticate."
            ) from err

        self._access_token = access_token
        self._access_token_expires = now + expires_in
        self._refresh_token = new_refresh

        # Persist rotated refresh token
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, "refresh_token": new_refresh},
        )

        return access_token

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch air quality data from ecobee.

        Returns dict keyed by thermostat name slug:
        {
            "edgewater_road": {
                "thermostat": "Edgewater Road",
                "co2_ppm": 450,
                "voc_ppb": 120,
                "aq_score": 85,
                "aq_accuracy": 2,
            },
            ...
        }
        """
        session = async_get_clientsession(self.hass)

        try:
            token = await self._ensure_token(session)
        except ConfigEntryAuthFailed:
            raise

        selection = json.dumps(
            {
                "selection": {
                    "selectionType": "registered",
                    "includeRuntime": True,
                    "includeEquipmentStatus": True,
                    "includeSettings": True,
                }
            }
        )

        try:
            async with session.get(
                ECOBEE_API,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                params={"json": selection},
            ) as resp:
                if resp.status == 401:
                    # Token expired mid-cycle, clear and retry once
                    self._access_token = None
                    self._access_token_expires = 0
                    try:
                        token = await self._ensure_token(session)
                    except ConfigEntryAuthFailed:
                        raise

                    async with session.get(
                        ECOBEE_API,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        params={"json": selection},
                    ) as retry_resp:
                        if retry_resp.status == 401:
                            raise ConfigEntryAuthFailed(
                                "Ecobee API returned 401 after token refresh"
                            )
                        retry_resp.raise_for_status()
                        data = await retry_resp.json()
                elif resp.status != 200:
                    raise UpdateFailed(
                        f"Ecobee API returned HTTP {resp.status}"
                    )
                else:
                    data = await resp.json()
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching ecobee data: {err}") from err

        results = {}
        for thermostat in data.get("thermostatList", []):
            name = thermostat.get("name", "Unknown")
            runtime = thermostat.get("runtime", {})
            voc = runtime.get("actualVOC", -5002)
            co2 = runtime.get("actualCO2", -5002)
            aq_score = runtime.get("actualAQScore", -5002)
            aq_accuracy = runtime.get("actualAQAccuracy", 0)

            # -5002 means sensor not available on this model
            if voc == -5002 and co2 == -5002:
                continue

            slug = name.lower().replace(" ", "_")
            results[slug] = {
                "thermostat": name,
                "co2_ppm": co2,
                "voc_ppb": voc,
                "aq_score": aq_score,
                "aq_accuracy": aq_accuracy,
                "equipment_status": thermostat.get("equipmentStatus", ""),
            }

            # Also pull equipment capability from settings
            settings = thermostat.get("settings", {})
            cool_stages = settings.get("coolStages")
            heat_stages = settings.get("heatStages")
            if cool_stages is not None:
                results[slug]["cool_stages"] = cool_stages
            if heat_stages is not None:
                results[slug]["heat_stages"] = heat_stages
            _LOGGER.debug(
                "%s - CO2: %d ppm, VOC: %d ppb, AQ Score: %d, Equipment: %s",
                name, co2, voc, aq_score,
                thermostat.get("equipmentStatus", ""),
            )

        if not results:
            _LOGGER.warning("No thermostats with air quality sensors found")

        return results
