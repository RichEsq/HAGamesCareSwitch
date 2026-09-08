"""Device-level services for the GamesCare RGB Switch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
import voluptuous as vol

from .api import MAX_TITLE_LENGTH
from .const import (
    ATTR_PORT,
    ATTR_TITLE,
    DOMAIN,
    SERVICE_RESET_PLAYTIME,
    SERVICE_SET_PORT_TITLE,
)

if TYPE_CHECKING:
    from .coordinator import GamesCareConfigEntry, GamesCareCoordinator

_PORT_SCHEMA = vol.All(vol.Coerce(int), vol.Range(min=1))

SET_PORT_TITLE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PORT): _PORT_SCHEMA,
        vol.Required(ATTR_TITLE): vol.All(cv.string, vol.Length(max=MAX_TITLE_LENGTH)),
    }
)

RESET_PLAYTIME_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_PORT): _PORT_SCHEMA,
    }
)


def _get_coordinator(hass: HomeAssistant, device_id: str) -> GamesCareCoordinator:
    """Resolve a device id to the coordinator of its loaded config entry."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device_id": device_id},
        )
    entry: GamesCareConfigEntry
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id in device.config_entries:
            if entry.state is not ConfigEntryState.LOADED:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="entry_not_loaded",
                    translation_placeholders={"device_id": device_id},
                )
            return entry.runtime_data
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="device_not_found",
        translation_placeholders={"device_id": device_id},
    )


def _validate_port(coordinator: GamesCareCoordinator, port: int) -> None:
    count = coordinator.data.ports.port_count
    if not 1 <= port <= count:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_port",
            translation_placeholders={"port": str(port), "count": str(count)},
        )


async def _async_set_port_title(call: ServiceCall) -> None:
    coordinator = _get_coordinator(call.hass, call.data[ATTR_DEVICE_ID])
    port: int = call.data[ATTR_PORT]
    _validate_port(coordinator, port)
    await coordinator.async_update_port(port, title=call.data[ATTR_TITLE])


async def _async_reset_playtime(call: ServiceCall) -> None:
    coordinator = _get_coordinator(call.hass, call.data[ATTR_DEVICE_ID])
    port: int = call.data[ATTR_PORT]
    _validate_port(coordinator, port)
    await coordinator.async_update_port(port, reset_playtime=True)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's services."""
    hass.services.async_register(
        DOMAIN, SERVICE_SET_PORT_TITLE, _async_set_port_title, schema=SET_PORT_TITLE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_PLAYTIME, _async_reset_playtime, schema=RESET_PLAYTIME_SCHEMA
    )
