"""Support for Frontier Silicon Devices (Medion, Hama, Auna,...)."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from afsapi import (
    AFSAPI,
    ConnectionError as FSConnectionError,
    FSApiException,
    PlayState,
)
import voluptuous as vol

from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    BrowseError,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    REPEAT_MODE_OFF,
    SUPPORT_BROWSE_MEDIA,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_REPEAT_SET,
    SUPPORT_SEEK,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    STATE_IDLE,
    STATE_OFF,
    STATE_OPENING,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .browse_media import browse_node, browse_top_level
from .const import DEFAULT_PIN, DEFAULT_PORT, DOMAIN, MEDIA_TYPE_PRESET

SUPPORT_FRONTIER_SILICON = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_STEP
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_SEEK
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_PLAY
    | SUPPORT_STOP
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_SELECT_SOUND_MODE
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_REPEAT_SET
    | SUPPORT_BROWSE_MEDIA
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PIN): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Frontier Silicon entity."""

    afsapi = hass.data[DOMAIN][config_entry.entry_id]  # type: AFSAPI

    async_add_entities([AFSAPIDevice(config_entry, afsapi)], True)


class AFSAPIDevice(MediaPlayerEntity):
    """Representation of a Frontier Silicon device on the network."""

    def __init__(self, config_entry: ConfigEntry, afsapi: AFSAPI) -> None:
        """Initialize the Frontier Silicon API device."""
        self._afsapi = afsapi

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, afsapi.webfsapi_endpoint)},
            name=config_entry.title,
        )
        self._attr_media_content_type = MEDIA_TYPE_CHANNEL
        self._attr_supported_features = SUPPORT_FRONTIER_SILICON
        self._attr_available = True

        self._attr_name = None
        self._attr_unique_id = None

        self._attr_source_list = None
        self._attr_source = None

        self._attr_sound_mode_list = None
        self._attr_sound_mode = None

        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_album_name = None

        self._attr_is_volume_muted = None
        self._attr_media_image_url = None

        self._attr_media_position = None
        self._attr_media_position_updated_at = None

        self._attr_shuffle = None
        self._attr_repeat = None

        self._max_volume = None
        self._attr_volume_level = None

        self.__modes_by_label = None
        self.__sound_modes_by_label = None

    async def async_update(self):
        """Get the latest date and update device state."""
        afsapi = self._afsapi

        try:
            if await afsapi.get_power():
                status = await afsapi.get_play_status()
                self._attr_state = {
                    PlayState.PLAYING: STATE_PLAYING,
                    PlayState.PAUSED: STATE_PAUSED,
                    PlayState.STOPPED: STATE_IDLE,
                    PlayState.LOADING: STATE_OPENING,
                    None: STATE_IDLE,
                }.get(status, STATE_UNKNOWN)
            else:
                self._attr_state = STATE_OFF
        except FSConnectionError:
            if self._attr_available:
                _LOGGER.warning(
                    "Could not connect to %s. Did it go offline?",
                    self._attr_name or afsapi.webfsapi_endpoint,
                )
                self._attr_state = STATE_UNAVAILABLE
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "Reconnected to %s",
                    self._attr_name or afsapi.webfsapi_endpoint,
                )

                self._attr_available = True
            if not self._attr_name:
                self._attr_name = await afsapi.get_friendly_name()

            if not self._attr_unique_id:
                try:
                    self._attr_unique_id = await afsapi.get_radio_id()
                except FSApiException:
                    self._attr_unique_id = self._attr_name

            if not self._attr_source_list:
                self.__modes_by_label = {
                    mode.label: mode.key for mode in await afsapi.get_modes()
                }
                self._attr_source_list = list(self.__modes_by_label.keys())

                # Getting the current mode upon initialisation allows us to set the
                # path correctly when browsing
                self._attr_source = (await afsapi.get_mode()).label

            if not self._attr_sound_mode_list:
                self.__sound_modes_by_label = {
                    sound_mode.label: sound_mode.key
                    for sound_mode in await afsapi.get_equalisers()
                }
                self._attr_sound_mode_list = list(self.__sound_modes_by_label.keys())

            # The API seems to include 'zero' in the number of steps (e.g. if the range is
            # 0-40 then get_volume_steps returns 41) subtract one to get the max volume.
            # If call to get_volume fails set to 0 and try again next time.
            if not self._max_volume:
                self._max_volume = int(await afsapi.get_volume_steps() or 1) - 1

        if self._attr_state not in [STATE_OFF, STATE_UNAVAILABLE]:
            info_name = await afsapi.get_play_name()
            info_text = await afsapi.get_play_text()

            self._attr_media_title = " - ".join(filter(None, [info_name, info_text]))
            self._attr_media_artist = await afsapi.get_play_artist()
            self._attr_media_album_name = await afsapi.get_play_album()

            self._attr_source = (await afsapi.get_mode()).label

            self._attr_sound_mode = (await afsapi.get_eq_preset()).label
            self._attr_is_volume_muted = await afsapi.get_mute()
            self._attr_media_image_url = await afsapi.get_play_graphic()

            self._attr_media_position = await afsapi.get_play_position()
            self._attr_media_position_updated_at = datetime.now()

            self._attr_shuffle = await afsapi.get_play_shuffle()
            self._attr_repeat = await afsapi.get_play_repeat()

            volume = await self._afsapi.get_volume()

            # Prevent division by zero if max_volume not known yet
            self._attr_volume_level = float(volume or 0) / (self._max_volume or 1)
        else:
            self._attr_media_title = None
            self._attr_media_artist = None
            self._attr_media_album_name = None

            # Don't reset _attr_source as it allows for browsing the player
            # while the device is shut off.

            self._attr_sound_mode = None
            self._attr_is_volume_muted = None
            self._attr_media_image_url = None

            self._attr_media_position = None
            self._attr_media_position_updated_at = None

            self._attr_shuffle = None
            self._attr_repeat = None

            self._attr_volume_level = None

    # Management actions
    # power control
    async def async_turn_on(self):
        """Turn on the device."""
        await self._afsapi.set_power(True)

    async def async_turn_off(self):
        """Turn off the device."""
        await self._afsapi.set_power(False)

    async def async_media_play(self):
        """Send play command."""
        await self._afsapi.play()

    async def async_media_pause(self):
        """Send pause command."""
        await self._afsapi.pause()

    async def async_media_play_pause(self):
        """Send play/pause command."""
        if self.state == STATE_PLAYING:
            await self._afsapi.pause()
        else:
            await self._afsapi.play()

    async def async_media_stop(self):
        """Send play/pause command."""
        await self._afsapi.pause()

    async def async_media_previous_track(self):
        """Send previous track command (results in rewind)."""
        await self._afsapi.rewind()

    async def async_media_next_track(self):
        """Send next track command (results in fast-forward)."""
        await self._afsapi.forward()

    async def async_media_seek(self, position):
        """Send seek command."""
        await self._afsapi.set_play_position(position)

    async def async_set_shuffle(self, shuffle):
        """Send shuffle command."""
        await self._afsapi.set_play_shuffle(shuffle)

    async def async_set_repeat(self, repeat):
        """Send repeat command."""
        await self._afsapi.set_play_repeat(repeat != REPEAT_MODE_OFF)

    # mute
    async def async_mute_volume(self, mute):
        """Send mute command."""
        await self._afsapi.set_mute(mute)

    # volume
    async def async_volume_up(self):
        """Send volume up command."""
        volume = await self._afsapi.get_volume()
        volume = int(volume or 0) + 1
        await self._afsapi.set_volume(min(volume, self._max_volume))

    async def async_volume_down(self):
        """Send volume down command."""
        volume = await self._afsapi.get_volume()
        volume = int(volume or 0) - 1
        await self._afsapi.set_volume(max(volume, 0))

    async def async_set_volume_level(self, volume):
        """Set volume command."""
        if self._max_volume:  # Can't do anything sensible if not set
            volume = int(volume * self._max_volume)
            await self._afsapi.set_volume(volume)

    async def async_select_source(self, source):
        """Select input source."""
        await self._afsapi.set_power(True)
        await self._afsapi.set_mode(self.__modes_by_label.get(source))

    async def async_select_sound_mode(self, sound_mode):
        """Select EQ Preset."""
        await self._afsapi.set_eq_preset(self.__sound_modes_by_label[sound_mode])

    async def async_browse_media(self, media_content_type=None, media_content_id=None):
        """Browse media library and preset stations."""
        if media_content_type in (None, "library"):
            return await browse_top_level(self._attr_source, self._afsapi)

        return await browse_node(self._afsapi, media_content_type, media_content_id)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Play selected media or channel."""
        supported_media_types = [MEDIA_TYPE_CHANNEL, MEDIA_TYPE_PRESET]

        if media_type not in supported_media_types:
            _LOGGER.error(
                "Got %s, but frontier_silicon only supports playing media types: %s",
                media_type,
                supported_media_types,
            )
            return

        keys = media_id.split("/")

        # check if we need to change mode
        desired_source = keys[0]
        if self._attr_source != desired_source:
            await self.async_select_source(desired_source)

        if media_type == MEDIA_TYPE_PRESET:
            if len(keys) != 2:
                raise BrowseError("Presets can only have 1 level")

            # Keys of presets are 0-based, while the list shown on the device starts from 1
            preset = int(keys[-1]) - 1

            result = await self._afsapi.select_preset(preset)
        else:
            result = await self._afsapi.nav_select_item_via_path(keys[1:])

        await self.async_update()

        return result
