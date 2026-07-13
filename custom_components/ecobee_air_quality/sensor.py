"""Sensor platform for Ecobee Air Quality."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
from .coordinator import EcobeeAirQualityCoordinator

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecobee Air Quality sensors from a config entry."""
    coordinator: EcobeeAirQualityCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for thermostat_slug, thermostat_data in coordinator.data.items():
        thermostat_name = thermostat_data["thermostat"]
        for sensor_key, sensor_def in SENSOR_TYPES.items():
            entities.append(
                EcobeeAirQualitySensor(
                    coordinator=coordinator,
                    entry=entry,
                    thermostat_slug=thermostat_slug,
                    thermostat_name=thermostat_name,
                    sensor_key=sensor_key,
                    sensor_def=sensor_def,
                )
            )

    async_add_entities(entities)


class EcobeeAirQualitySensor(CoordinatorEntity, SensorEntity):
    """Representation of an Ecobee air quality sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcobeeAirQualityCoordinator,
        entry: ConfigEntry,
        thermostat_slug: str,
        thermostat_name: str,
        sensor_key: str,
        sensor_def: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._thermostat_slug = thermostat_slug
        self._sensor_key = sensor_key
        self._data_key = sensor_def["data_key"]

        # Entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{thermostat_slug}_{sensor_key}"
        self._attr_name = sensor_def["name"]
        self._attr_native_unit_of_measurement = sensor_def["native_unit_of_measurement"]
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = sensor_def["icon"]

        if sensor_def["device_class"]:
            self._attr_device_class = sensor_def["device_class"]

        # Device info groups sensors per thermostat
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{thermostat_slug}")},
            name=f"Ecobee {thermostat_name}",
            manufacturer="ecobee",
            model="Smart Thermostat",
            entry_type=None,
        )

    @property
    def native_value(self) -> int | str | None:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None
        thermostat_data = self.coordinator.data.get(self._thermostat_slug)
        if not thermostat_data:
            return None
        value = thermostat_data.get(self._data_key)
        if value == -5002:
            return None
        # Don't expose equipment_status for thermostats that don't have it
        if self._sensor_key == "equipment_status" and not value:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes for air quality score."""
        if self._sensor_key != "air_quality_score":
            return None
        if not self.coordinator.data:
            return None
        thermostat_data = self.coordinator.data.get(self._thermostat_slug)
        if not thermostat_data:
            return None
        return {"aq_accuracy": thermostat_data.get("aq_accuracy", 0)}

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled by default."""
        return True
