"""Make sure that existing Koogeek P1EU support isn't broken."""

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import POWER_WATT

from tests.components.homekit_controller.common import (
    DeviceTestInfo,
    EntityTestInfo,
    assert_devices_and_entities_created,
    setup_accessories_from_file,
    setup_test_accessories,
)


async def test_koogeek_p1eu_setup(hass):
    """Test that a Koogeek P1EU can be correctly setup in HA."""
    accessories = await setup_accessories_from_file(hass, "koogeek_p1eu.json")
    await setup_test_accessories(hass, accessories)

    await assert_devices_and_entities_created(
        hass,
        DeviceTestInfo(
            unique_id="00:00:00:00:00:00",
            name="Koogeek-P1-A00AA0",
            model="P1EU",
            manufacturer="Koogeek",
            sw_version="2.3.7",
            hw_version="",
            serial_number="EUCP03190xxxxx48",
            devices=[],
            entities=[
                EntityTestInfo(
                    entity_id="switch.koogeek_p1_a00aa0",
                    friendly_name="Koogeek-P1-A00AA0",
                    unique_id="homekit-EUCP03190xxxxx48-7",
                    state="off",
                ),
                EntityTestInfo(
                    entity_id="sensor.koogeek_p1_a00aa0_real_time_energy",
                    friendly_name="Koogeek-P1-A00AA0 - Real Time Energy",
                    unique_id="homekit-EUCP03190xxxxx48-aid:1-sid:21-cid:22",
                    unit_of_measurement=POWER_WATT,
                    capabilities={"state_class": SensorStateClass.MEASUREMENT},
                    state="5",
                ),
            ],
        ),
    )
