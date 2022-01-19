"""Config flow for Frontier Silicon Media Player integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_URL,
    CONF_PIN,
    CONF_USE_SESSION,
    CONF_WEBFSAPI_URL,
    DEFAULT_PIN,
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
        vol.Required(CONF_DEVICE_URL): str,
    }
)


STEP_DEVICE_CONFIG_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PIN, default=DEFAULT_PIN): str,
        vol.Required(CONF_USE_SESSION, default=False): bool,
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
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.exception(exception)
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

        errors = {}
        try:
            webfsapi_url = await validate_device_url(
                self.hass, user_input[CONF_DEVICE_URL]
            )
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.exception(exception)
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(webfsapi_url)
            self._abort_if_unique_id_configured()

            self.context.update({CONF_WEBFSAPI_URL: webfsapi_url})
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Process entity discovered via SSDP."""
        device_url = discovery_info.ssdp_location

        self.context.update(
            {
                "title_placeholders": {
                    "name": discovery_info.upnp.get(SSDP_ATTR_SPEAKER_NAME)
                }
            }
        )

        try:
            webfsapi_url = await validate_device_url(self.hass, device_url)

            await self.async_set_unique_id(webfsapi_url)
            self._abort_if_unique_id_configured()

            self.context.update({CONF_WEBFSAPI_URL: webfsapi_url})

            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="cannot_connect")

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle the import of legacy configuration.yaml entries."""

        try:
            webfsapi_url = await validate_device_url(
                self.hass, import_info.get(CONF_DEVICE_URL)
            )
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(webfsapi_url, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        name = import_info[CONF_NAME]

        _LOGGER.warning("Frontier Silicon %s imported from YAML config." % name)
        return self.async_create_entry(
            title=import_info[CONF_NAME],
            data={**import_info, CONF_WEBFSAPI_URL: webfsapi_url},
        )
