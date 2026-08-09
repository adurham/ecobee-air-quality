"""Button platform for Ecobee Enhanced — native write control.

Provides control actions via the real ecobee cloud API's Thermostat
Functions, instead of relying on the HomeKit bridge (which doesn't
attribute changes cleanly and doesn't expose hold/schedule state at all).
See: https://www.ecobee.com/home/developer/api/documentation/v1/functions/using-functions.shtml
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EcobeeEnhancedCoordinator

_LOGGER = logging.getLogger(__name__)


# holdType "indefinite" holds until manually resumed (matches what the
# thermostat itself calls "Hold Until I Change"). "nextTransition" would
# instead auto-resume at the next scheduled comfort setting change.
_HOLD_CLIMATES = {
    "resume_program": None,  # special-cased: calls resumeProgram, not setHold
    "hold_home": "home",
    "hold_away": "away",
    "hold_sleep": "sleep",
}

_BUTTON_DEFS = {
    "resume_program": {
        "name": "Resume Program",
        "icon": "mdi:calendar-refresh",
    },
    "hold_home": {
        "name": "Hold Home",
        "icon": "mdi:home-thermometer",
    },
    "hold_away": {
        "name": "Hold Away",
        "icon": "mdi:home-export-outline",
    },
    "hold_sleep": {
        "name": "Hold Sleep",
        "icon": "mdi:sleep",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecobee Enhanced buttons from a config entry."""
    coordinator: EcobeeEnhancedCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for thermostat_slug, thermostat_data in coordinator.data.items():
        thermostat_name = thermostat_data["thermostat"]
        for button_key, button_def in _BUTTON_DEFS.items():
            entities.append(
                EcobeeEnhancedButton(
                    coordinator=coordinator,
                    entry=entry,
                    thermostat_slug=thermostat_slug,
                    thermostat_name=thermostat_name,
                    button_key=button_key,
                    button_def=button_def,
                )
            )

    async_add_entities(entities)


class EcobeeEnhancedButton(CoordinatorEntity, ButtonEntity):
    """A control action (resume program / hold on a climate)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcobeeEnhancedCoordinator,
        entry: ConfigEntry,
        thermostat_slug: str,
        thermostat_name: str,
        button_key: str,
        button_def: dict,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._thermostat_slug = thermostat_slug
        self._button_key = button_key

        self._attr_unique_id = f"{entry.entry_id}_{thermostat_slug}_{button_key}"
        self._attr_name = button_def["name"]
        self._attr_icon = button_def["icon"]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{thermostat_slug}")},
            name=f"Ecobee {thermostat_name}",
            manufacturer="ecobee",
            model="Smart Thermostat",
            entry_type=None,
        )

    async def async_press(self) -> None:
        """Handle the button press — call the matching ecobee Function."""
        thermostat_data = self.coordinator.data.get(self._thermostat_slug, {})
        identifier = thermostat_data.get("identifier") or None

        if self._button_key == "resume_program":
            _LOGGER.info(
                "Ecobee Enhanced: resuming program for %s", self._thermostat_slug
            )
            await self.coordinator.async_call_function(
                "resumeProgram",
                params={"resumeAll": True},
                thermostat_identifier=identifier,
            )
            return

        climate_ref = _HOLD_CLIMATES[self._button_key]
        _LOGGER.info(
            "Ecobee Enhanced: setting hold on climate %r for %s",
            climate_ref,
            self._thermostat_slug,
        )
        await self.coordinator.async_call_function(
            "setHold",
            params={
                "holdType": "indefinite",
                "holdClimateRef": climate_ref,
            },
            thermostat_identifier=identifier,
        )

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled by default."""
        return True
