"""Validation logic for Config Flow of Frontier Silicon Media Player integration."""
from __future__ import annotations

from typing import Any

from afsapi import AFSAPI, FSApiException

from homeassistant.exceptions import HomeAssistantError


async def validate_device_url(device_url: str | None) -> str:
    """Validate the device_url."""

    try:
        return await AFSAPI.get_webfsapi_endpoint(device_url)
    except FSApiException as fsapi_exception:
        raise CannotConnect from fsapi_exception


async def validate_device_config(webfsapi_url: str, pin: str) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    try:
        afsapi = AFSAPI(webfsapi_url, pin)

        friendly_name = await afsapi.get_friendly_name()

        # Return info that you want to store in the config entry.
        return {
            "title": friendly_name,
        }

    except FSApiException as fsapi_exception:
        if str(fsapi_exception).startswith("Access denied"):
            raise InvalidAuth from fsapi_exception
        raise CannotConnect from fsapi_exception


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
