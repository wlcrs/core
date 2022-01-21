"""Config flow for Frontier Silicon Media Player integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_PIN,
    CONF_WEBFSAPI_URL,
    DEFAULT_PIN,
    DEFAULT_PORT,
    DOMAIN,
    SSDP_ATTR_SPEAKER_NAME,
    SSDP_ST,
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
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)

STEP_DEVICE_CONFIG_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_PIN,
            default=DEFAULT_PIN,
            description="Can be found via 'MENU button > Main Menu > System setting > Network > NetRemote PIN setup'",
        ): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Frontier Silicon Media Player."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""

        self._webfsapi_url: str | None = None
        self._name: str | None = None

    async def async_step_import(self, import_info: dict[str, Any]) -> FlowResult:
        """Handle the import of legacy configuration.yaml entries."""

        device_url = f"http://{import_info[CONF_HOST]}:{import_info[CONF_PORT]}/device"
        try:
            self._webfsapi_url = await validate_device_url(device_url)
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception while fetching webfsapi url")
            return self.async_abort(reason="unknown")

        # For manually added devices the unique_id is the webfsapi_url,
        # for devices discovered through SSDP it is the UDN
        await self.async_set_unique_id(self._webfsapi_url, raise_on_progress=False)
        self._abort_if_unique_id_configured()

        self._name = import_info[CONF_NAME]

        _LOGGER.warning("Frontier Silicon %s imported from YAML config." % self._name)
        return await self._create_entry(pin=import_info[CONF_PIN])

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step of manual configuration."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        device_url = f"http://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}/device"
        try:
            self._webfsapi_url = await validate_device_url(device_url)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception while fetching webfsapi url")
            errors["base"] = "unknown"
        else:

            # For manually added devices the unique_id is the webfsapi_url,
            # for devices discovered through SSDP it is the UDN
            await self.async_set_unique_id(self._webfsapi_url)
            self._abort_if_unique_id_configured()

            return await self._async_step_device_config_if_needed()

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
            self._webfsapi_url = await validate_device_url(device_url)
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unexpected failure to retrieve webfsapi url from discovered device"
            )
            return self.async_abort(reason="unknown")

        # For manually added devices the unique_id is the webfsapi_url,
        # for devices discovered through SSDP it is the UDN
        await self.async_set_unique_id(discovery_info.ssdp_udn)
        self._abort_if_unique_id_configured(
            updates={CONF_WEBFSAPI_URL: self._webfsapi_url}, reload_on_update=True
        )

        return await self._async_step_device_config_if_needed(show_confirm=True)

    async def async_step_unignore(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Rediscover previously ignored devices by their unique_id."""
        if not user_input or "unique_id" not in user_input:
            return self.async_abort(reason="unknown")

        udn = user_input.get("unique_id")
        assert udn

        # Find a discovery matching the unignored unique_id for a Frontier Silicon device
        discovery = await ssdp.async_get_discovery_info_by_udn_st(
            self.hass, udn, SSDP_ST
        )
        if not discovery:
            return self.async_abort(reason="discovery_error")

        return await self.async_step_ssdp(discovery_info=discovery)

    async def _async_step_device_config_if_needed(self, show_confirm=False):

        try:
            # try to login with default pin
            info = await validate_device_config(self._webfsapi_url, DEFAULT_PIN)

            self._name = info["title"]
            if show_confirm:
                return await self.async_step_confirm()
            else:
                return await self._create_entry()
        except InvalidAuth:
            pass  # Ask for a PIN

        return await self.async_step_device_config()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow the user to confirm adding the device."""
        _LOGGER.debug("async_step_confirm: %s", user_input)

        if user_input is not None:
            return await self._create_entry()

        self._set_confirm_only()
        return self.async_show_form(step_id="confirm")

    async def async_step_device_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device configuration step.

        We ask for the PIN in this step.
        """
        assert self._webfsapi_url is not None

        if user_input is None:
            return self.async_show_form(
                step_id="device_config", data_schema=STEP_DEVICE_CONFIG_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_device_config(
                self._webfsapi_url, user_input[CONF_PIN]
            )
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.exception(exception)
            errors["base"] = "unknown"
        else:
            self._name = info["title"]

            return await self._create_entry(pin=user_input[CONF_PIN])

        return self.async_show_form(
            step_id="device_config",
            data_schema=STEP_DEVICE_CONFIG_DATA_SCHEMA,
            errors=errors,
        )

    async def _create_entry(self, pin: str | None = None):
        """Create the entry."""
        assert self._name is not None
        assert self._webfsapi_url is not None

        return self.async_create_entry(
            title=self._name,
            data={CONF_WEBFSAPI_URL: self._webfsapi_url, CONF_PIN: pin or DEFAULT_PIN},
        )
