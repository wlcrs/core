"""Test the Frontier Silicon config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.components.frontier_silicon.config_flow import (
    CannotConnect,
    InvalidAuth,
)
from homeassistant.components.frontier_silicon.const import (
    CONF_DEVICE_URL,
    CONF_USE_SESSION,
    DOMAIN,
)
from homeassistant.const import CONF_NAME, CONF_PIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import (
    RESULT_TYPE_ABORT,
    RESULT_TYPE_CREATE_ENTRY,
    RESULT_TYPE_FORM,
)

from tests.common import MockConfigEntry


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1/webfsapi",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
        return_value={
            "pin": "1234",
            "use_session": False,
            "title": "Name of the device",
        },
    ), patch(
        "homeassistant.components.frontier_silicon.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"pin": "1234", "use_session": False},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result3["title"] == "Name of the device"
    assert result3["data"] == {
        "webfsapi_url": "http://1.1.1.1/webfsapi",
        "pin": "1234",
        "use_session": False,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_invalid_device_url(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
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

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        side_effect=ValueError,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_invalid_pin(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1/webfsapi",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
        side_effect=InvalidAuth,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"pin": "1244", "use_session": False},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {"base": "invalid_auth"}


async def test_device_config_connection_error(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1/webfsapi",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
        side_effect=CannotConnect,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"pin": "1244", "use_session": False},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {"base": "cannot_connect"}


async def test_device_config_unexpected_error(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1/webfsapi",
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == RESULT_TYPE_FORM
    assert result2["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_config",
        side_effect=ValueError,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"pin": "1244", "use_session": False},
        )
        await hass.async_block_till_done()

    assert result3["type"] == RESULT_TYPE_FORM
    assert result3["errors"] == {"base": "unknown"}


async def test_config_flow_device_exists(hass):
    """Test config flow aborts on already configured devices."""
    MockConfigEntry(
        domain="frontier_silicon",
        unique_id="http://1.1.1.1:80/webfsapi",
        data={
            "webfsapi_url": "http://1.1.1.1:80/webfsapi",
            "pin": "1234",
            "use_session": False,
        },
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["errors"] is None

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1:80/webfsapi",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_url": "http://1.1.1.1/device",
            },
        )

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"


async def test_ssdp(hass):
    """Test a device being discovered."""

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1/webfsapi",
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "user"


async def test_ssdp_fail(hass):
    """Test a device being discovered but failing to reply."""

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        side_effect=CannotConnect,
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=ssdp.SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://1.1.1.1/device",
                upnp={"SPEAKER-NAME": "Speaker Name"},
            ),
        )

    assert result["type"] == RESULT_TYPE_ABORT
    assert result["reason"] == "cannot_connect"


async def test_import(hass: HomeAssistant) -> None:
    """Test import."""

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1:80/webfsapi",
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_DEVICE_URL: "http://1.1.1.1:80/device",
                CONF_PIN: "1234",
                CONF_USE_SESSION: False,
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == RESULT_TYPE_CREATE_ENTRY

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        side_effect=CannotConnect,
    ):

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_DEVICE_URL: "http://1.1.1.1:80/device",
                CONF_PIN: "1234",
                CONF_USE_SESSION: False,
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == RESULT_TYPE_ABORT
        assert result["reason"] == "cannot_connect"


async def test_import_already_exists(hass: HomeAssistant) -> None:
    """Test import of device which already exists."""
    MockConfigEntry(
        domain="frontier_silicon",
        unique_id="http://1.1.1.1:80/webfsapi",
        data={
            "webfsapi_url": "http://1.1.1.1:80/webfsapi",
            "pin": "1234",
            "use_session": False,
        },
    ).add_to_hass(hass)

    with patch(
        "homeassistant.components.frontier_silicon.config_flow.validate_device_url",
        return_value="http://1.1.1.1:80/webfsapi",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                CONF_DEVICE_URL: "http://1.1.1.1:80/device",
                CONF_PIN: "1234",
                CONF_USE_SESSION: False,
                CONF_NAME: "Test name",
            },
        )

        assert result["type"] == "abort"
        assert result["reason"] == "already_configured"
