"""Tests for the playtime and active-port sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    EntityCategory,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import HOST, FakeSwitch


async def test_playtime_disabled_by_default(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    registry = er.async_get(hass)
    entry = registry.async_get_entity_id("sensor", "gamescare", f"{HOST}_port_1_playtime")
    assert entry is not None
    reg_entry = registry.async_get(entry)
    assert reg_entry is not None
    assert reg_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert reg_entry.entity_category is EntityCategory.DIAGNOSTIC
    assert hass.states.get(entry) is None


async def test_playtime_when_enabled(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", "gamescare", f"{HOST}_port_8_playtime")
    assert entity_id == "sensor.gcswitch_port_8_playtime"
    registry.async_update_entity(entity_id, disabled_by=None)
    await hass.config_entries.async_reload(init_integration.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "1234"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.DURATION
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTime.SECONDS
    assert state.attributes["state_class"] == SensorStateClass.TOTAL_INCREASING
    assert state.attributes["port"] == 8


async def test_active_port_sensor(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    state = hass.states.get("sensor.gcswitch_active_port")
    assert state is not None
    assert state.state == "8"
    assert state.attributes["title"] == ""
    entry = er.async_get(hass).async_get("sensor.gcswitch_active_port")
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
