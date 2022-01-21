"""Test the Frontier Silicon config flow."""
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.components.frontier_silicon.config_flow import (
    CannotConnect,
    InvalidAuth,
)
from homeassistant.components.frontier_silicon.const import (
    CONF_WEBFSAPI_URL,
    DEFAULT_PIN,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PIN, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry

valid_validate_device_url = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
    return_value="http://1.1.1.1:80/webfsapi",
)

invalid_validate_device_url = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
    side_effect=CannotConnect,
)

unexpected_error_validate_device_url = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
    side_effect=ValueError,
)

mock_existing_entry = MockConfigEntry(
    domain="frontier_silicon",
    unique_id="http://1.1.1.1:80/webfsapi",
    data={
        "webfsapi_url": "http://1.1.1.1:80/webfsapi",
        "pin": "1234",
        "use_session": False,
    },
)

valid_validate_device_config = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
    return_value={
        "title": "Name of the device",
    },
)

invalid_pin_validate_device_config = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
    side_effect=InvalidAuth,
)

connect_error_validate_device_config = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
    side_effect=CannotConnect,
)

unexpected_error_validate_device_config = patch(
    "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
    side_effect=ValueError,
)


async def test_import(hass: HomeAssistant) -> None:
    """Test import."""

    with valid_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 80,
                CONF_PIN: "1234",
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == RESULT_TYPE_CREATE_ENTRY

    with invalid_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 80,
                CONF_PIN: "1234",
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "cannot_connect"

    with unexpected_error_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 80,
                CONF_PIN: "1234",
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "unknown"


async def test_import_already_exists(hass: HomeAssistant) -> None:
    """Test import of device which already exists."""
    mock_existing_entry.add_to_hass(hass)

    with valid_validate_device_url:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 80,
                CONF_PIN: "1234",
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_form_default_pin(hass: HomeAssistant) -> None:
    """Test manual device add with default pin."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with valid_validate_device_url, valid_validate_device_config, patch(
        "homeassistant.components.frontier_silicon.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_PORT: 80},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Name of the device"
    assert result2["data"] == {
        "webfsapi_url": "http://1.1.1.1:80/webfsapi",
        "pin": "1234",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_nondefault_pin(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with valid_validate_device_url, invalid_pin_validate_device_config:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_PORT: 80},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with valid_validate_device_config, patch(
        "homeassistant.components.frontier_silicon.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result3["title"] == "Name of the device"
    assert result3["data"] == {
        "webfsapi_url": "http://1.1.1.1:80/webfsapi",
        "pin": "4321",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_nondefault_pin_invalid(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with valid_validate_device_url, invalid_pin_validate_device_config:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_PORT: 80},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with invalid_pin_validate_device_config:
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {"base": "invalid_auth"}


async def test_invalid_device_url(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with invalid_validate_device_url:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_PORT: 80},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_device_url_unexpected_error(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with unexpected_error_validate_device_url:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.1.1.1", CONF_PORT: 80},
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_ssdp(hass):
    """Test a device being discovered."""

    with valid_validate_device_config, valid_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_udn="mock_udn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Name of the device"
    assert result2["data"] == {
        CONF_WEBFSAPI_URL: "http://1.1.1.1:80/webfsapi",
        CONF_PIN: DEFAULT_PIN,
    }


async def test_ssdp_nondefault_pin(hass):
    """Test a device being discovered."""

    with valid_validate_device_url, invalid_pin_validate_device_config:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_udn="mock_udn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "device_config"

    with connect_error_validate_device_config:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "cannot_connect"}

    with unexpected_error_validate_device_config:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}

    with valid_validate_device_config, patch(
        "homeassistant.components.frontier_silicon.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PIN: "4321"},
        )

    assert result2["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Name of the device"
    assert result2["data"] == {
        CONF_WEBFSAPI_URL: "http://1.1.1.1:80/webfsapi",
        CONF_PIN: "4321",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_ssdp_fail(hass):
    """Test a device being discovered but failing to reply."""
    with unexpected_error_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_udn="mock_udn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "unknown"

    with invalid_validate_device_url:

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_udn="mock_udn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "cannot_connect"


async def test_unignore_flow(hass: HomeAssistant):
    """Test the unignore flow happy path."""

    none_mock = AsyncMock(return_value=None)

    with patch.object(ssdp, "async_get_discovery_info_by_udn_st", none_mock):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_UNIGNORE},
            data={"unique_id": "mock_udn"},
        )

        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "discovery_error"

    found_mock = AsyncMock(
        return_value=ssdp.SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_udn="mock_udn",
            ssdp_st="mock_st",
            ssdp_location="http://1.1.1.1/device",
            upnp={"SPEAKER-NAME": "Speaker Name"},
        )
    )

    with patch.object(
        ssdp,
        "async_get_discovery_info_by_udn_st",
        found_mock,
    ), valid_validate_device_url, valid_validate_device_config:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_UNIGNORE},
            data={"unique_id": "mock_udn"},
        )

        assert result["type"] == RESULT_TYPE_FORM
        assert result["step_id"] == "confirm"


async def test_unignore_flow_invalid(hass: HomeAssistant):
    """Test the unignore flow with empty input."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_UNIGNORE},
        data={},
    )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "unknown"
