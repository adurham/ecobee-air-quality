"""Sensor platform for Ecobee Enhanced."""

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
from .coordinator import EcobeeEnhancedCoordinator

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecobee Enhanced sensors from a config entry."""
    coordinator: EcobeeEnhancedCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for thermostat_slug, thermostat_data in coordinator.data.items():
        thermostat_name = thermostat_data["thermostat"]
        for sensor_key, sensor_def in SENSOR_TYPES.items():
            entities.append(
                EcobeeEnhancedSensor(
                    coordinator=coordinator,
                    entry=entry,
                    thermostat_slug=thermostat_slug,
                    thermostat_name=thermostat_name,
                    sensor_key=sensor_key,
                    sensor_def=sensor_def,
                )
            )

        # Remote sensors (ecobee3 pucks) are variable per-household, so they
        # can't be fixed SENSOR_TYPES entries. One HA entity per physical
        # sensor per capability it actually reports (temperature/occupancy/
        # humidity), discovered from the first coordinator refresh.
        for rs_id, rs_data in thermostat_data.get("remote_sensors", {}).items():
            for cap_key in ("temperature_f", "occupancy", "humidity_pct"):
                if cap_key not in rs_data:
                    continue
                entities.append(
                    EcobeeRemoteSensor(
                        coordinator=coordinator,
                        entry=entry,
                        thermostat_slug=thermostat_slug,
                        thermostat_name=thermostat_name,
                        remote_sensor_id=rs_id,
                        remote_sensor_name=rs_data.get("name", rs_id),
                        capability_key=cap_key,
                    )
                )

    async_add_entities(entities)


class EcobeeEnhancedSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Ecobee Enhanced sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcobeeEnhancedCoordinator,
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
        # state_class from the sensor def; equipment_status is a string
        # (CSV like "compCool1,fan") so it has no state_class.
        if sensor_def["state_class"] is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_state_class = None
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
        # equipment_status is a CSV string (e.g. "compCool1,fan") or empty.
        # Return None only if truly empty, so HA shows "unknown" for idle
        # equipment rather than a stale restored state.
        if self._sensor_key == "equipment_status" and not value:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return additional attributes for air quality score / climate_count."""
        if not self.coordinator.data:
            return None
        thermostat_data = self.coordinator.data.get(self._thermostat_slug)
        if not thermostat_data:
            return None
        if self._sensor_key == "air_quality_score":
            return {"aq_accuracy": thermostat_data.get("aq_accuracy", 0)}
        if self._sensor_key == "climate_count":
            # Full climate definitions (setpoints, fan mode per comfort
            # setting) and the 7x48 weekly schedule grid. Too structured
            # for a scalar state, so it rides as attributes on the count
            # sensor — use a template sensor or automation to pull specific
            # values out of these if you need them elsewhere.
            return {
                "climates": thermostat_data.get("climates", {}),
                "schedule": thermostat_data.get("schedule", []),
            }
        if self._sensor_key == "latest_alert_severity":
            # Carry the acknowledgeRef so the Acknowledge Function's button
            # (or a script) can reference it without a separate sensor.
            return {"acknowledge_ref": thermostat_data.get("latest_alert_ref", "")}
        return None


    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled by default."""
        return True


_REMOTE_SENSOR_CAP_DEFS = {
    "temperature_f": {
        "name_suffix": "Temperature",
        "device_class": "temperature",
        "native_unit_of_measurement": "°F",
        "icon": "mdi:thermometer",
    },
    "occupancy": {
        "name_suffix": "Occupancy",
        "device_class": None,
        "native_unit_of_measurement": None,
        "icon": "mdi:motion-sensor",
    },
    "humidity_pct": {
        "name_suffix": "Humidity",
        "device_class": "humidity",
        "native_unit_of_measurement": "%",
        "icon": "mdi:water-percent",
    },
}


class EcobeeRemoteSensor(CoordinatorEntity, SensorEntity):
    """Representation of one capability of one ecobee3 remote sensor puck."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcobeeEnhancedCoordinator,
        entry: ConfigEntry,
        thermostat_slug: str,
        thermostat_name: str,
        remote_sensor_id: str,
        remote_sensor_name: str,
        capability_key: str,
    ) -> None:
        """Initialize the remote sensor capability entity."""
        super().__init__(coordinator)
        self._thermostat_slug = thermostat_slug
        self._remote_sensor_id = remote_sensor_id
        self._capability_key = capability_key
        cap_def = _REMOTE_SENSOR_CAP_DEFS[capability_key]

        self._attr_unique_id = (
            f"{entry.entry_id}_{thermostat_slug}_rs_{remote_sensor_id}_{capability_key}"
        )
        self._attr_name = f"{remote_sensor_name} {cap_def['name_suffix']}"
        self._attr_native_unit_of_measurement = cap_def["native_unit_of_measurement"]
        self._attr_state_class = (
            "measurement" if capability_key != "occupancy" else None
        )
        self._attr_icon = cap_def["icon"]
        if cap_def["device_class"]:
            self._attr_device_class = cap_def["device_class"]

        # Group under the SAME device as the parent thermostat's sensors so
        # remote sensor readings show up alongside CO2/VOC/equipment status
        # for that thermostat, not as a separate orphan device.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{thermostat_slug}")},
            name=f"Ecobee {thermostat_name}",
            manufacturer="ecobee",
            model="Smart Thermostat",
            entry_type=None,
        )

    @property
    def native_value(self):
        """Return the remote sensor capability value."""
        if not self.coordinator.data:
            return None
        thermostat_data = self.coordinator.data.get(self._thermostat_slug)
        if not thermostat_data:
            return None
        rs_data = thermostat_data.get("remote_sensors", {}).get(self._remote_sensor_id)
        if not rs_data:
            return None
        return rs_data.get(self._capability_key)

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled by default."""
        return True
