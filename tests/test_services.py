"""Tests for the set_port_title and reset_playtime services."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.gamescare.const import (
    DOMAIN,
    SERVICE_RESET_PLAYTIME,
    SERVICE_SET_PORT_TITLE,
)

from .conftest import HOST, FakeSwitch


def _device_id(hass: HomeAssistant) -> str:
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, HOST)})
    assert device is not None
    return device.id


async def test_services_registered(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    assert hass.services.has_service(DOMAIN, SERVICE_SET_PORT_TITLE)
    assert hass.services.has_service(DOMAIN, SERVICE_RESET_PLAYTIME)


async def test_set_port_title(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_PORT_TITLE,
        {"device_id": _device_id(hass), "port": 3, "title": "Saturn"},
        blocking=True,
    )
    (call,) = fake_switch.calls_for("POST", "ports")
    assert call[2] == {"port": "3", "title": "Saturn"}

    # The returned state is pushed straight into the entities.
    select = hass.states.get("select.gcswitch_input")
    assert select.attributes["port_titles"]["Port 3"] == "Saturn"
    signal = hass.states.get("binary_sensor.gcswitch_port_3_signal")
    assert signal.attributes["title"] == "Saturn"
    assert signal.attributes["friendly_name"] == "gcswitch Saturn signal"


async def test_reset_playtime(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESET_PLAYTIME,
        {"device_id": _device_id(hass), "port": "8"},
        blocking=True,
    )
    (call,) = fake_switch.calls_for("POST", "ports")
    assert call[2] == {"port": "8", "resetplaytime": "true"}
    assert fake_switch.ports["ports"][7]["playtime"] == 0


async def test_title_too_long_rejected(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_PORT_TITLE,
            {"device_id": _device_id(hass), "port": 1, "title": "x" * 17},
            blocking=True,
        )
    assert fake_switch.calls_for("POST", "ports") == []


async def test_port_out_of_range(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    with pytest.raises(ServiceValidationError, match="out of range"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_PLAYTIME,
            {"device_id": _device_id(hass), "port": 9},
            blocking=True,
        )
    assert fake_switch.calls_for("POST", "ports") == []


async def test_unknown_device(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError, match="not a GamesCare"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_PLAYTIME,
            {"device_id": "does-not-exist", "port": 1},
            blocking=True,
        )


async def test_device_from_other_integration(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    other = MockConfigEntry(domain="other", entry_id="other_entry")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("other", "x")}
    )
    with pytest.raises(ServiceValidationError, match="not a GamesCare"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_PLAYTIME,
            {"device_id": device.id, "port": 1},
            blocking=True,
        )


async def test_entry_not_loaded(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    device_id = _device_id(hass)
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError, match="not loaded"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_PLAYTIME,
            {"device_id": device_id, "port": 1},
            blocking=True,
        )
