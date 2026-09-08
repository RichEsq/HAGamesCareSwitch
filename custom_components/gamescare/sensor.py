"""Sensor platform: per-port playtime and the active port number."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime

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
    """Set up playtime sensors for each port plus the active-port sensor."""
    coordinator = entry.runtime_data
    entities: list[GamesCareEntity] = [
        GamesCarePortPlaytimeSensor(coordinator, port.number)
        for port in coordinator.data.ports.ports
    ]
    entities.append(GamesCareActivePortSensor(coordinator))
    async_add_entities(entities)


class GamesCarePortPlaytimeSensor(GamesCarePortEntity, SensorEntity):
    """Accumulated seconds this port has been the active input."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _suffix = "playtime"

    def __init__(self, coordinator: GamesCareCoordinator, port_number: int) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, port_number, "playtime")

    @property
    def native_value(self) -> int | None:
        """Return the playtime in seconds."""
        port = self.port
        return None if port is None else port.playtime

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the port number and title."""
        port = self.port
        return {
            ATTR_PORT: self.port_number,
            ATTR_TITLE: "" if port is None else port.title,
        }


class GamesCareActivePortSensor(GamesCareEntity, SensorEntity):
    """The currently selected port number (0 when none)."""

    _attr_translation_key = "active_port"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GamesCareCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "active_port")

    @property
    def native_value(self) -> int:
        """Return the active port number."""
        return self.coordinator.data.ports.active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the active port's title, if any."""
        state = self.coordinator.data.ports
        port = state.get_port(state.active)
        return {ATTR_TITLE: "" if port is None else port.title}
