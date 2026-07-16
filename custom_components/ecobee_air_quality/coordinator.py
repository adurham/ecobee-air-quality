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
                    "includeExtendedRuntime": True,
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
                "humidity": runtime.get("actualHumidity"),
            }

            # Parse equipmentStatus CSV into live compressor/fan stage sensors.
            # ecobee equipmentStatus is a CSV like "compCool1,fan" or
            # "compCool2,fan" or "auxHeat1,compHeat2,fan" or "" (idle).
            # compCoolN = compressor cooling stage N (1 or 2)
            # compHeatN = compressor heating stage N (1 or 2)
            # auxHeatN  = auxiliary (resistive) heat stage N
            # fan       = blower running
            equip = thermostat.get("equipmentStatus", "")
            parts = [p.strip() for p in equip.split(",") if p.strip()]
            cool_stage = 0
            heat_stage = 0
            fan_on = 0
            for part in parts:
                if part.startswith("compCool"):
                    try:
                        cool_stage = int(part[len("compCool"):])
                    except ValueError:
                        cool_stage = 1
                elif part.startswith("compHeat"):
                    try:
                        heat_stage = int(part[len("compHeat"):])
                    except ValueError:
                        heat_stage = 1
                elif part == "fan":
                    fan_on = 1
            results[slug]["compressor_cool_stage"] = cool_stage
            results[slug]["compressor_heat_stage"] = heat_stage
            results[slug]["fan_running"] = fan_on

            # Pull per-stage runtime seconds from extendedRuntime.
            # Each array has 3 values (last 3 5-min intervals); use the most
            # recent (last element). Values are 0-300 seconds.
            ext = thermostat.get("extendedRuntime", {})
            if ext:
                def _last(arr):
                    """Return the last element of a 3-element array, or 0."""
                    if isinstance(arr, list) and arr:
                        try:
                            return int(arr[-1])
                        except (ValueError, TypeError):
                            return 0
                    return 0
                results[slug]["cool1_runtime_seconds"] = _last(ext.get("cool1"))
                results[slug]["cool2_runtime_seconds"] = _last(ext.get("cool2"))
                results[slug]["aux_heat1_runtime_seconds"] = _last(ext.get("auxHeat1"))
                results[slug]["aux_heat2_runtime_seconds"] = _last(ext.get("auxHeat2"))
                results[slug]["aux_heat3_runtime_seconds"] = _last(ext.get("auxHeat3"))
                results[slug]["heat_pump1_runtime_seconds"] = _last(ext.get("heatPump1"))
                results[slug]["heat_pump2_runtime_seconds"] = _last(ext.get("heatPump2"))
                results[slug]["fan_runtime_seconds"] = _last(ext.get("fan"))
                results[slug]["dehumidifier_runtime_seconds"] = _last(ext.get("dehumidifier"))
                results[slug]["humidifier_runtime_seconds"] = _last(ext.get("humidifier"))
                results[slug]["ventilator_runtime_seconds"] = _last(ext.get("ventilator"))
                results[slug]["economizer_runtime_seconds"] = _last(ext.get("economizer"))
                # dmOffset = dehumidify overcool offset in tenths of a degree F
                # (e.g. 8 = 0.8°F below setpoint). Convert to °F.
                dm_offset = _last(ext.get("dmOffset"))
                results[slug]["dehumidify_overcool_offset"] = dm_offset / 10.0

            # Live dehumidify target from runtime (changes with comfort settings)
            desired_dehum = runtime.get("desiredDehumidity")
            if desired_dehum is not None and desired_dehum != -5002:
                results[slug]["desired_dehumidity"] = desired_dehum

            # Also pull equipment capability from settings
            settings = thermostat.get("settings", {})

            # ---- Staging / threshold / config fields from the settings block ----
            # ecobee settings API exposes ONLY stage1* thresholds. There is NO
            # stage2CoolingDifferentialTemp key — stage-2 engagement is governed
            # by an internal ecobee algorithm (rate of temp change, stage-1
            # runtime, outdoor temp if connected) that is not readable via the
            # consumer API. The only way to know stage 2 engaged is the live
            # compressor_cool_stage sensor above. See warm fact / SKILL.md.
            #
            # Temperature values in the settings API are in TENTHS of a degree F
            # (e.g. 10 -> 1.0F). Convert to F for the sensors. Time values are
            # in SECONDS except fanMinOnTime / ventilatorMinOnTime which are in
            # MINUTES.
            def _to_f(raw, default=None):
                """Convert ecobee tenths-of-F to degrees F, or default if absent."""
                if raw is None or raw == "":
                    return default
                try:
                    return int(raw) / 10.0
                except (ValueError, TypeError):
                    return default

            def _to_s(raw, default=None):
                """Pass through a seconds value (int), or default if absent."""
                if raw is None or raw == "":
                    return default
                try:
                    return int(raw)
                except (ValueError, TypeError):
                    return default

            def _to_min(raw, default=None):
                """Pass through a minutes value (int), or default if absent."""
                if raw is None or raw == "":
                    return default
                try:
                    return int(raw)
                except (ValueError, TypeError):
                    return default

            # Staging thresholds (the answer to "when does the compressor stage")
            stage1_cool_diff = settings.get("stage1CoolingDifferentialTemp")
            if stage1_cool_diff is not None:
                results[slug]["stage1_cooling_differential_temp_f"] = _to_f(stage1_cool_diff)
            stage1_heat_diff = settings.get("stage1HeatingDifferentialTemp")
            if stage1_heat_diff is not None:
                results[slug]["stage1_heating_differential_temp_f"] = _to_f(stage1_heat_diff)
            stage1_cool_diss = settings.get("stage1CoolingDissipationTime")
            if stage1_cool_diss is not None:
                results[slug]["stage1_cooling_dissipation_time_s"] = _to_s(stage1_cool_diss)
            stage1_heat_diss = settings.get("stage1HeatingDissipationTime")
            if stage1_heat_diss is not None:
                results[slug]["stage1_heating_dissipation_time_s"] = _to_s(stage1_heat_diss)
            comp_prot_time = settings.get("compressorProtectionMinTime")
            if comp_prot_time is not None:
                results[slug]["compressor_protection_min_time_s"] = _to_s(comp_prot_time)
            comp_prot_temp = settings.get("compressorProtectionMinTemp")
            if comp_prot_temp is not None:
                results[slug]["compressor_protection_min_temp_f"] = _to_f(comp_prot_temp)
            heat_cool_min_delta = settings.get("heatCoolMinDelta")
            if heat_cool_min_delta is not None:
                results[slug]["heat_cool_min_delta_f"] = _to_f(heat_cool_min_delta)

            # Setpoint ranges (the envelope the user can choose within)
            results[slug]["cool_range_high_f"] = _to_f(settings.get("coolRangeHigh"))
            results[slug]["cool_range_low_f"] = _to_f(settings.get("coolRangeLow"))
            results[slug]["heat_range_high_f"] = _to_f(settings.get("heatRangeHigh"))
            results[slug]["heat_range_low_f"] = _to_f(settings.get("heatRangeLow"))

            # Fan / ventilation config
            results[slug]["fan_min_on_time_min"] = _to_min(settings.get("fanMinOnTime"))
            results[slug]["ventilator_min_on_time_min"] = _to_min(settings.get("ventilatorMinOnTime"))
            results[slug]["ventilator_min_on_time_home_min"] = _to_min(settings.get("ventilatorMinOnTimeHome"))
            results[slug]["ventilator_min_on_time_away_min"] = _to_min(settings.get("ventilatorMinOnTimeAway"))
            results[slug]["smart_circulation"] = bool(settings.get("smartCirculation", False))
            results[slug]["ventilator_free_cooling"] = bool(settings.get("ventilatorFreeCooling", False))

            # Dehumidification config (live settings, not the runtime target)
            dehum_level = settings.get("dehumidifierLevel")
            if dehum_level is not None:
                results[slug]["dehumidifier_level_pct"] = dehum_level
            results[slug]["dehumidify_overcool_offset_config"] = _to_f(settings.get("dehumidifyOvercoolOffset"))
            results[slug]["dehumidifier_mode"] = settings.get("dehumidifierMode")
            results[slug]["dehumidify_with_ac"] = bool(settings.get("dehumidifyWithAC", False))
            results[slug]["dehumidify_when_heating"] = bool(settings.get("dehumidifyWhenHeating", False))

            # Equipment capability / system type flags
            results[slug]["has_heat_pump"] = bool(settings.get("hasHeatPump", False))
            results[slug]["has_forced_air"] = bool(settings.get("hasForcedAir", False))
            results[slug]["has_boiler"] = bool(settings.get("hasBoiler", False))
            results[slug]["has_humidifier"] = bool(settings.get("hasHumidifier", False))
            results[slug]["has_dehumidifier"] = bool(settings.get("hasDehumidifier", False))
            results[slug]["use_zone_controller"] = bool(settings.get("useZoneController", False))

            # Top-level mode flags
            results[slug]["hvac_mode_setting"] = settings.get("hvacMode")
            results[slug]["follow_me_comfort"] = bool(settings.get("followMeComfort", False))
            results[slug]["auto_heat_cool_enabled"] = bool(settings.get("autoHeatCoolFeatureEnabled", False))
            results[slug]["cooling_lockout"] = bool(settings.get("coolingLockout", False))

            # Static stage capability (already exposed as cool_stages/heat_stages
            # above — kept for back-compat with existing sensors)
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
