"""Binary sensor platform: per-port signal detection and auto mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from .const import ATTR_PORT, ATTR_TITLE
from .entity import GamesCareEntity, GamesCarePortEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import GamesCareConfigEntry, GamesCareCoordinator


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GamesCareConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for each port plus the auto-mode sensor."""
    coordinator = entry.runtime_data
    entities: list[GamesCareEntity] = [
        GamesCarePortSignalSensor(coordinator, port.number) for port in coordinator.data.ports.ports
    ]
    entities.append(GamesCareAutoModeSensor(coordinator))
    async_add_entities(entities)


class GamesCarePortSignalSensor(GamesCarePortEntity, BinarySensorEntity):
    """On when the switch detects sync on this input."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _suffix = "signal"

    def __init__(self, coordinator: GamesCareCoordinator, port_number: int) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, port_number, "signal")

    @property
    def is_on(self) -> bool | None:
        """Return True when sync is detected."""
        port = self.port
        return None if port is None else port.detected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the port number and title."""
        port = self.port
        return {
            ATTR_PORT: self.port_number,
            ATTR_TITLE: "" if port is None else port.title,
        }


class GamesCareAutoModeSensor(GamesCareEntity, BinarySensorEntity):
    """On when the switch is in auto-detect mode (no forced port)."""

    _attr_translation_key = "auto_mode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GamesCareCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "auto_mode")

    @property
    def is_on(self) -> bool:
        """Return True when no port is forced."""
        return not self.coordinator.data.ports.forced
