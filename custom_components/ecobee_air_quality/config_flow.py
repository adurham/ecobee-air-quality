"""Config flow for Ecobee Air Quality integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .auth import AuthError, EcobeeAuth, MFARequired
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcobeeAirQualityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ecobee Air Quality."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._auth = EcobeeAuth()
        self._reauth_entry = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - ecobee login."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input.get("email", "").strip()
            password = user_input.get("password", "").strip()
            refresh_token = user_input.get("refresh_token", "").strip()

            if refresh_token:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Ecobee Air Quality",
                    data={"refresh_token": refresh_token},
                )

            if not email or not password:
                errors["base"] = "missing_credentials"
            else:
                try:
                    access_token, refresh_token = (
                        await self._auth.async_login(email, password)
                    )
                except MFARequired:
                    return await self.async_step_mfa()
                except AuthError as err:
                    _LOGGER.error("Ecobee login failed")
                    if "Invalid email or password" in str(err):
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "login_failed"
                else:
                    if not refresh_token:
                        errors["base"] = "no_refresh_token"
                    else:
                        await self.async_set_unique_id(DOMAIN)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title="Ecobee Air Quality",
                            data={"refresh_token": refresh_token},
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional("email"): str,
                    vol.Optional("password"): str,
                    vol.Optional("refresh_token"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle MFA code entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mfa_code = user_input.get("mfa_code", "").strip()
            if not mfa_code:
                errors["base"] = "missing_mfa_code"
            else:
                try:
                    access_token, refresh_token = (
                        await self._auth.async_submit_mfa(mfa_code)
                    )
                except AuthError as err:
                    _LOGGER.error("MFA verification failed")
                    if "Invalid" in str(err):
                        errors["base"] = "invalid_mfa_code"
                    else:
                        errors["base"] = "mfa_failed"
                else:
                    if not refresh_token:
                        errors["base"] = "no_refresh_token"
                    else:
                        await self.async_set_unique_id(DOMAIN)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title="Ecobee Air Quality",
                            data={"refresh_token": refresh_token},
                        )

        return self.async_show_form(
            step_id="mfa",
            data_schema=vol.Schema(
                {
                    vol.Required("mfa_code"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when refresh token fails."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input.get("email", "").strip()
            password = user_input.get("password", "").strip()
            refresh_token = user_input.get("refresh_token", "").strip()

            if refresh_token:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={"refresh_token": refresh_token},
                )

            if not email or not password:
                errors["base"] = "missing_credentials"
            else:
                try:
                    _, new_refresh = await self._auth.async_login(
                        email, password
                    )
                except MFARequired:
                    return await self.async_step_reauth_mfa()
                except AuthError as err:
                    _LOGGER.error("Ecobee reauth failed")
                    if "Invalid email or password" in str(err):
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "login_failed"
                else:
                    if not new_refresh:
                        errors["base"] = "no_refresh_token"
                    else:
                        return self.async_update_reload_and_abort(
                            self._reauth_entry,
                            data={"refresh_token": new_refresh},
                        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional("email"): str,
                    vol.Optional("password"): str,
                    vol.Optional("refresh_token"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle MFA during reauth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mfa_code = user_input.get("mfa_code", "").strip()
            if not mfa_code:
                errors["base"] = "missing_mfa_code"
            else:
                try:
                    _, new_refresh = await self._auth.async_submit_mfa(
                        mfa_code
                    )
                except AuthError as err:
                    _LOGGER.error("Reauth MFA verification failed")
                    if "Invalid" in str(err):
                        errors["base"] = "invalid_mfa_code"
                    else:
                        errors["base"] = "mfa_failed"
                else:
                    if not new_refresh:
                        errors["base"] = "no_refresh_token"
                    else:
                        return self.async_update_reload_and_abort(
                            self._reauth_entry,
                            data={"refresh_token": new_refresh},
                        )

        return self.async_show_form(
            step_id="reauth_mfa",
            data_schema=vol.Schema(
                {
                    vol.Required("mfa_code"): str,
                }
            ),
            errors=errors,
        )
