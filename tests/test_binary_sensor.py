"""Tests for the per-port signal and auto-mode binary sensors."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from .conftest import HOST, FakeSwitch


async def test_signal_sensors(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    registry = er.async_get(hass)
    for number in range(1, 9):
        entity_id = f"binary_sensor.gcswitch_port_{number}_signal"
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == ("on" if number == 8 else "off")
        assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.CONNECTIVITY
        assert state.attributes[ATTR_FRIENDLY_NAME] == f"gcswitch Port {number} signal"
        assert state.attributes["port"] == number
        assert state.attributes["title"] == ""
        entry = registry.async_get(entity_id)
        assert entry is not None
        assert entry.unique_id == f"{HOST}_port_{number}_signal"
        assert entry.entity_category is None


async def test_signal_updates_on_poll(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    fake_switch: FakeSwitch,
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_switch.ports["ports"][2]["detected"] = True
    freezer.tick(timedelta(seconds=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.gcswitch_port_3_signal").state == "on"


async def test_title_changes_name_not_entity_id(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.ports["ports"][2]["title"] = "Saturn"
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.gcswitch_port_3_signal")
    assert state is not None
    assert state.attributes[ATTR_FRIENDLY_NAME] == "gcswitch Saturn signal"
    assert state.attributes["title"] == "Saturn"
    assert hass.states.get("binary_sensor.gcswitch_saturn_signal") is None


async def test_auto_mode_sensor(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    state = hass.states.get("binary_sensor.gcswitch_auto_mode")
    assert state is not None
    assert state.state == "off"
    entry = er.async_get(hass).async_get("binary_sensor.gcswitch_auto_mode")
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
