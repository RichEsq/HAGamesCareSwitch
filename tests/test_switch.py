"""Tests for the backlight switch."""

from __future__ import annotations

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeSwitch

ENTITY_ID = "switch.gcswitch_backlight"


async def test_backlight(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    assert hass.states.get(ENTITY_ID).state == "on"
    entry = er.async_get(hass).async_get(ENTITY_ID)
    assert entry is not None
    assert entry.entity_category is EntityCategory.CONFIG

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert hass.states.get(ENTITY_ID).state == "off"
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert hass.states.get(ENTITY_ID).state == "on"

    posts = [c[2] for c in fake_switch.calls_for("POST", "settings")]
    assert posts == [{"backlight": "0"}, {"backlight": "1"}]
    # Settings are re-read after each write so state reflects the device.
    assert len(fake_switch.calls_for("GET", "settings")) == 3


async def test_backlight_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.offline = True
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )
    assert hass.states.get(ENTITY_ID).state == "on"
