"""Diagnostics support for the GamesCare RGB Switch integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import GamesCareConfigEntry

TO_REDACT = {CONF_HOST, "address", "ssid", "gbs_ip", "pixelfx_ip", "pixelfx_user"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GamesCareConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "ports": asdict(data.ports),
        "settings": async_redact_data(asdict(data.settings), TO_REDACT),
    }
