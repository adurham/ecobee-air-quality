"""Ecobee Enhanced integration for Home Assistant."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import EcobeeEnhancedCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "button"]

# ---- Service schemas ----
# These cover the remaining ecobee Thermostat Functions that need
# parameters (temps, text, durations) and so don't fit the parameterless
# button.py entities. All services target every coordinator in this
# config entry's data (single-thermostat households, which is the only
# case exercised so far); a future multi-thermostat setup would need a
# thermostat_identifier selector added here.

SERVICE_SET_HOLD_TEMP = "set_hold_temperature"
SERVICE_SET_HOLD_TEMP_SCHEMA = vol.Schema(
    {
        vol.Required("heat_temp_f"): vol.Coerce(float),
        vol.Required("cool_temp_f"): vol.Coerce(float),
        vol.Optional("hold_type", default="indefinite"): vol.In(
            ["indefinite", "nextTransition", "askMe"]
        ),
    }
)

SERVICE_CREATE_VACATION = "create_vacation"
SERVICE_CREATE_VACATION_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("heat_temp_f"): vol.Coerce(float),
        vol.Required("cool_temp_f"): vol.Coerce(float),
        vol.Required("start_date"): cv.string,  # "YYYY-MM-DD"
        vol.Required("start_time"): cv.string,  # "HH:MM:SS"
        vol.Required("end_date"): cv.string,
        vol.Required("end_time"): cv.string,
    }
)

SERVICE_DELETE_VACATION = "delete_vacation"
SERVICE_DELETE_VACATION_SCHEMA = vol.Schema({vol.Required("name"): cv.string})

SERVICE_SEND_MESSAGE = "send_message"
SERVICE_SEND_MESSAGE_SCHEMA = vol.Schema({vol.Required("text"): cv.string})

SERVICE_SET_OCCUPIED = "set_occupied"
SERVICE_SET_OCCUPIED_SCHEMA = vol.Schema(
    {
        vol.Required("occupied"): cv.boolean,
        vol.Optional("hold_type", default="indefinite"): vol.In(
            ["indefinite", "nextTransition"]
        ),
    }
)

SERVICE_ACKNOWLEDGE_ALERT = "acknowledge_alert"
SERVICE_ACKNOWLEDGE_ALERT_SCHEMA = vol.Schema(
    {
        vol.Required("acknowledge_ref"): cv.string,
        vol.Optional("ack_type", default="accept"): vol.In(
            ["accept", "decline", "defer"]
        ),
    }
)

# Pure fan-only hold — sets ONLY the fan, no temperature setpoints. Per
# ecobee's SetHold docs, passing "fan" without heatHoldTemp/coolHoldTemp
# creates an event with isTemperatureAbsolute=isTemperatureRelative=false
# (a "fan hold"), so the schedule's own setpoints keep being honored.
# Added 2026-08-09: replaces the smart_vent_controller AppDaemon app's old
# climate/set_fan_mode call against the HomeKit Controller entity, which
# is a documented HA bug (home-assistant/core#92010) — ANY fan-mode write
# via HomeKit forces an indefinite temperature hold on ecobee's side, with
# no clean way to tell it apart from a real comfort-setting hold. Going
# through this integration's real cloud API avoids that entirely.
SERVICE_SET_FAN_HOLD = "set_fan_hold"
SERVICE_SET_FAN_HOLD_SCHEMA = vol.Schema(
    {
        vol.Optional("fan_mode", default="on"): vol.In(["on", "auto"]),
        vol.Optional("hold_type", default="indefinite"): vol.In(
            ["indefinite", "nextTransition", "askMe"]
        ),
    }
)

# Releases ONLY the most recently pushed hold event (resumeAll=false pops
# the top of ecobee's event stack). Distinct from button.*_resume_program,
# which calls resumeAll=true and clears EVERY hold. Callers like FAN-ASSIST
# must use this one — resumeAll=true would also wipe out a real user hold
# (e.g. Hold Away) sitting underneath the transient fan hold.
SERVICE_RESUME_TOP_EVENT = "resume_top_event"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecobee Enhanced from a config entry."""
    coordinator = EcobeeEnhancedCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass, coordinator)
    return True


def _async_register_services(
    hass: HomeAssistant, coordinator: EcobeeEnhancedCoordinator
) -> None:
    """Register write-side ecobee Thermostat Functions as HA services.

    Idempotent — re-registering an already-registered service just
    replaces the handler, which matters when this integration entry is
    reloaded without a full HA restart.
    """

    async def _handle_set_hold_temperature(call: ServiceCall) -> None:
        heat_f = call.data["heat_temp_f"]
        cool_f = call.data["cool_temp_f"]
        hold_type = call.data["hold_type"]
        await coordinator.async_call_function(
            "setHold",
            params={
                "holdType": hold_type,
                "heatHoldTemp": round(heat_f * 10),
                "coolHoldTemp": round(cool_f * 10),
            },
        )

    async def _handle_create_vacation(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "createVacation",
            params={
                "name": call.data["name"],
                "heatHoldTemp": round(call.data["heat_temp_f"] * 10),
                "coolHoldTemp": round(call.data["cool_temp_f"] * 10),
                "startDate": call.data["start_date"],
                "startTime": call.data["start_time"],
                "endDate": call.data["end_date"],
                "endTime": call.data["end_time"],
            },
        )

    async def _handle_delete_vacation(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "deleteVacation", params={"name": call.data["name"]}
        )

    async def _handle_send_message(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "sendMessage", params={"text": call.data["text"]}
        )

    async def _handle_set_occupied(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "setOccupied",
            params={
                "occupied": call.data["occupied"],
                "holdType": call.data["hold_type"],
            },
        )

    async def _handle_acknowledge_alert(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "acknowledge",
            params={
                "ackRef": call.data["acknowledge_ref"],
                "ackType": call.data["ack_type"],
            },
        )

    async def _handle_set_fan_hold(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "setHold",
            params={
                "holdType": call.data["hold_type"],
                "fan": call.data["fan_mode"],
            },
        )

    async def _handle_resume_top_event(call: ServiceCall) -> None:
        await coordinator.async_call_function(
            "resumeProgram", params={"resumeAll": False}
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HOLD_TEMP,
        _handle_set_hold_temperature,
        schema=SERVICE_SET_HOLD_TEMP_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_VACATION,
        _handle_create_vacation,
        schema=SERVICE_CREATE_VACATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_VACATION,
        _handle_delete_vacation,
        schema=SERVICE_DELETE_VACATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        _handle_send_message,
        schema=SERVICE_SEND_MESSAGE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_OCCUPIED,
        _handle_set_occupied,
        schema=SERVICE_SET_OCCUPIED_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE_ALERT,
        _handle_acknowledge_alert,
        schema=SERVICE_ACKNOWLEDGE_ALERT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_HOLD,
        _handle_set_fan_hold,
        schema=SERVICE_SET_FAN_HOLD_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESUME_TOP_EVENT,
        _handle_resume_top_event,
        schema=vol.Schema({}),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Only remove services once no other config entry needs them
        # (relevant if a future multi-account setup adds a second entry).
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_SET_HOLD_TEMP,
                SERVICE_CREATE_VACATION,
                SERVICE_DELETE_VACATION,
                SERVICE_SEND_MESSAGE,
                SERVICE_SET_OCCUPIED,
                SERVICE_ACKNOWLEDGE_ALERT,
                SERVICE_SET_FAN_HOLD,
                SERVICE_RESUME_TOP_EVENT,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok
