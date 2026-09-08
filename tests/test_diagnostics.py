"""Tests for config entry diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
) -> None:
    result = await get_diagnostics_for_config_entry(hass, hass_client, init_integration)

    assert result["entry"]["data"] == {"host": "**REDACTED**"}
    assert result["entry"]["options"] == {"scan_interval": 15}
    assert result["ports"]["active"] == 8
    assert result["ports"]["forced"] is True
    assert len(result["ports"]["ports"]) == 8
    assert result["ports"]["ports"][0]["number"] == 1
    settings = result["settings"]
    assert settings["version"] == "3.1.2"
    assert settings["ssid"] == "**REDACTED**"
    assert settings["address"] == "**REDACTED**"
    assert settings["pixelfx_user"] == "**REDACTED**"
