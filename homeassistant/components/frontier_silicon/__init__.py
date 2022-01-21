"""The Frontier Silicon integration."""
from __future__ import annotations

import asyncio

from afsapi import AFSAPI

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PLATFORM,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_PIN, CONF_WEBFSAPI_URL, DEFAULT_PIN, DEFAULT_PORT, DOMAIN

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Perform migration from YAML config to Config Flow entity."""

    async def _migrate_entry(entry_to_migrate):
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_NAME: entry_to_migrate.get(CONF_NAME),
                CONF_HOST: entry_to_migrate.get(CONF_HOST),
                CONF_PORT: entry_to_migrate.get(CONF_PORT, DEFAULT_PORT),
                CONF_PIN: entry_to_migrate.get(CONF_PASSWORD, DEFAULT_PIN),
            },
        )

    tasks = []
    for entry_to_migrate in config.get("media_player", []):
        if entry_to_migrate.get(CONF_PLATFORM) == DOMAIN:
            tasks.append(asyncio.create_task(_migrate_entry(entry_to_migrate)))

    async def async_tasks_cancel(_event):
        """Cancel config flow import tasks."""
        for task in tasks:
            if not task.done():
                task.cancel()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, async_tasks_cancel)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Frontier Silicon from a config entry."""

    webfsapi_url = entry.data[CONF_WEBFSAPI_URL]
    pin = entry.data[CONF_PIN]

    afsapi = AFSAPI(webfsapi_url, pin)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = afsapi

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
