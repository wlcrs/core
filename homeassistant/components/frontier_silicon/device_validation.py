"""Validation logic for Config Flow of Frontier Silicon Media Player integration."""
from __future__ import annotations

from typing import Any

from afsapi import AFSAPI


async def validate_device_url(device_url: str | None) -> str:
    """Validate the device_url."""

    return await AFSAPI.get_webfsapi_endpoint(device_url)


async def validate_device_config(webfsapi_url: str, pin: str) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    afsapi = AFSAPI(webfsapi_url, pin)

    friendly_name = await afsapi.get_friendly_name()

    # Return info that you want to store in the config entry.
    return {
        "title": friendly_name,
    }
