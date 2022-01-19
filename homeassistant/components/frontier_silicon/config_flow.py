"""Config flow for Frontier Silicon Media Player integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_URL,
    CONF_PIN,
    CONF_USE_SESSION,
    CONF_WEBFSAPI_URL,
    DOMAIN,
    SSDP_ATTR_SPEAKER_NAME,
)
from .device_validation import (
    CannotConnect,
    InvalidAuth,
    validate_device_config,
    validate_device_url,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("device_url"): str,
    }
)


STEP_DEVICE_CONFIG_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("pin", default="1234"): str,
        vol.Required("use_session", default=False): bool,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frontier Silicon Media Player."""

    VERSION = 1

    async def async_step_device_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device configuration step.

        This step is called when the FSAPI URL has successfully been found.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="device_config", data_schema=STEP_DEVICE_CONFIG_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_device_config(
                self.hass,
                self.context[CONF_WEBFSAPI_URL],
                user_input[CONF_PIN],
                user_input[CONF_USE_SESSION],
            )
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            data = {**user_input, CONF_WEBFSAPI_URL: self.context[CONF_WEBFSAPI_URL]}
            return self.async_create_entry(title=info["title"], data=data)

        return self.async_show_form(
            step_id="device_config",
            data_schema=STEP_DEVICE_CONFIG_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        await self.async_set_unique_id(user_input[CONF_DEVICE_URL])
        self._abort_if_unique_id_configured()

        errors = {}

        try:
            webfsapi_url = await validate_device_url(
                self.hass, user_input[CONF_DEVICE_URL]
            )
            self.context.update({CONF_WEBFSAPI_URL: webfsapi_url})
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Process entity discovered via SSDP."""
        device_url = discovery_info.ssdp_location

        await self.async_set_unique_id(device_url)
        self._abort_if_unique_id_configured()

        self.context.update(
            {
                "title_placeholders": {
                    "name": discovery_info.upnp.get(SSDP_ATTR_SPEAKER_NAME)
                }
            }
        )

        try:
            webfsapi_url = await validate_device_url(self.hass, device_url)

            self.context.update({CONF_WEBFSAPI_URL: webfsapi_url})

            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="cannot_connect")
