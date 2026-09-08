"""Tests for setup, unload, availability and coordinator polling."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.gamescare.const import DOMAIN

from .conftest import BASE_URL, HOST, FakeSwitch


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: int) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    entry = init_integration
    assert entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, HOST)})
    assert device is not None
    assert device.manufacturer == "GamesCare"
    assert device.model == "RGB Switch"
    assert device.sw_version == "3.1.2"
    assert device.name == "gcswitch"
    assert device.configuration_url == BASE_URL

    # First refresh reads settings once and ports once.
    assert len(fake_switch.calls_for("GET", "settings")) == 1
    assert len(fake_switch.calls_for("GET", "ports")) == 1

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_offline(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.offline = True
    mock_config_entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_entities_unavailable_then_recover(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    fake_switch: FakeSwitch,
    freezer: FrozenDateTimeFactory,
) -> None:
    assert hass.states.get("select.gcswitch_input").state == "Port 8"

    fake_switch.offline = True
    await _advance(hass, freezer, 16)
    assert hass.states.get("select.gcswitch_input").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.gcswitch_port_1_signal").state == STATE_UNAVAILABLE

    fake_switch.offline = False
    await _advance(hass, freezer, 16)
    assert hass.states.get("select.gcswitch_input").state == "Port 8"
    assert hass.states.get("binary_sensor.gcswitch_port_1_signal").state == "off"


async def test_bad_payload_marks_unavailable(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    fake_switch: FakeSwitch,
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_switch.garbage = True
    await _advance(hass, freezer, 16)
    assert hass.states.get("select.gcswitch_input").state == STATE_UNAVAILABLE


async def test_settings_polled_less_often_than_ports(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    fake_switch: FakeSwitch,
    freezer: FrozenDateTimeFactory,
) -> None:
    for _ in range(4):
        await _advance(hass, freezer, 15)
    assert len(fake_switch.calls_for("GET", "ports")) == 5
    assert len(fake_switch.calls_for("GET", "settings")) == 1

    # After the settings refresh interval (300 s) settings are read again.
    for _ in range(20):
        await _advance(hass, freezer, 15)
    assert len(fake_switch.calls_for("GET", "settings")) == 2
