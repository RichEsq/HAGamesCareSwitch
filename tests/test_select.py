"""Tests for the input select."""

from __future__ import annotations

from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gamescare.select import option_to_port, port_option

from .conftest import FakeSwitch

ENTITY_ID = "select.gcswitch_input"


async def _select(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: option},
        blocking=True,
    )


def test_option_helpers() -> None:
    assert port_option(3) == "Port 3"
    assert option_to_port("Auto") == 0
    assert option_to_port("Port 3") == 3
    assert option_to_port("Port x") is None
    assert option_to_port("Saturn") is None


async def test_initial_state(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "Port 8"
    assert state.attributes[ATTR_OPTIONS] == ["Auto", *(f"Port {n}" for n in range(1, 9))]
    assert state.attributes["active_port"] == 8
    assert state.attributes["forced"] is True
    assert state.attributes["port_titles"] == {f"Port {n}": "" for n in range(1, 9)}
    assert state.attributes["friendly_name"] == "gcswitch Input"


async def test_select_port_pushes_state(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    await _select(hass, "Port 3")
    forces = [c[1].query.get("force") for c in fake_switch.calls_for("GET", "ports")]
    assert forces[-1] == "3"
    # State updated from the response without waiting for the next poll.
    state = hass.states.get(ENTITY_ID)
    assert state.state == "Port 3"
    assert state.attributes["active_port"] == 3
    assert hass.states.get("sensor.gcswitch_active_port").state == "3"


async def test_select_auto(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    await _select(hass, "Auto")
    forces = [c[1].query.get("force") for c in fake_switch.calls_for("GET", "ports")]
    assert forces[-1] == "0"
    state = hass.states.get(ENTITY_ID)
    assert state.state == "Auto"
    assert state.attributes["active_port"] == 0
    assert state.attributes["forced"] is False
    assert hass.states.get("binary_sensor.gcswitch_auto_mode").state == "on"


async def test_select_out_of_range(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await _select(hass, "Port 9")


async def test_select_device_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.offline = True
    with pytest.raises(HomeAssistantError, match="Could not reach"):
        await _select(hass, "Port 2")
    # State unchanged.
    assert hass.states.get(ENTITY_ID).state == "Port 8"


async def test_forced_with_unknown_active_is_unknown(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.ports["active"] = 0
    fake_switch.ports["forced"] = 1
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unknown"
