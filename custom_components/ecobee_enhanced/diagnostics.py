"""Diagnostics support for Ecobee Enhanced."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Sanitize: never expose tokens
    return {
        "entry_id": entry.entry_id,
        "has_refresh_token": bool(entry.data.get("refresh_token")),
        "coordinator_last_update_success": coordinator.last_update_success,
        "thermostat_count": len(coordinator.data) if coordinator.data else 0,
        "thermostats": {
            slug: {
                "name": data.get("thermostat"),
                "has_co2": data.get("co2_ppm", -5002) != -5002,
                "has_voc": data.get("voc_ppb", -5002) != -5002,
                "has_aq_score": data.get("aq_score", -5002) != -5002,
            }
            for slug, data in (coordinator.data or {}).items()
        },
    }
