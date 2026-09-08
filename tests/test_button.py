"""Tests for the reboot button."""

from __future__ import annotations

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    SERVICE_PRESS,
    ButtonDeviceClass,
)
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import FakeSwitch

ENTITY_ID = "button.gcswitch_reboot"


async def _press(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )


async def test_reboot(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_DEVICE_CLASS] == ButtonDeviceClass.RESTART
    entry = er.async_get(hass).async_get(ENTITY_ID)
    assert entry is not None
    assert entry.entity_category is EntityCategory.CONFIG

    await _press(hass)
    reboots = [c for c in fake_switch.calls_for("GET", "settings") if "reboot" in c[1].query]
    assert len(reboots) == 1
    assert reboots[0][1].query["reboot"] == "1"


async def test_reboot_tolerates_dropped_connection(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.drop_on_reboot = True
    await _press(hass)  # must not raise


async def test_reboot_api_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, fake_switch: FakeSwitch
) -> None:
    fake_switch.http_status = 500
    with pytest.raises(HomeAssistantError, match="Unexpected response"):
        await _press(hass)
