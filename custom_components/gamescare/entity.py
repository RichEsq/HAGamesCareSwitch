"""Base entities for the GamesCare RGB Switch integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL

if TYPE_CHECKING:
    from .api import Port
    from .coordinator import GamesCareCoordinator


class GamesCareEntity(CoordinatorEntity["GamesCareCoordinator"]):
    """Base entity sharing one device across all platforms."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GamesCareCoordinator, key: str) -> None:
        """Initialise the entity with a unique id derived from the entry."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=entry.title,
            sw_version=coordinator.data.settings.version,
            configuration_url=coordinator.client.base_url,
        )


class GamesCarePortEntity(GamesCareEntity):
    """Base entity bound to a single 1-based port number."""

    _suffix: str = ""
    """Suffix appended to the port name, e.g. ``signal``."""

    def __init__(self, coordinator: GamesCareCoordinator, port_number: int, key: str) -> None:
        """Initialise a per-port entity."""
        super().__init__(coordinator, f"port_{port_number}_{key}")
        self.port_number = port_number

    @property
    def port(self) -> Port | None:
        """Return the current state of this port, if the device reports it."""
        return self.coordinator.data.ports.get_port(self.port_number)

    @property
    def available(self) -> bool:
        """Unavailable if the device stops reporting this port."""
        return super().available and self.port is not None

    @property
    def name(self) -> str:
        """Use the port title when set, otherwise ``Port N``."""
        port = self.port
        base = port.display_name if port is not None else f"Port {self.port_number}"
        return f"{base} {self._suffix}".strip()

    @property
    def suggested_object_id(self) -> str:
        """Keep the entity id stable regardless of the (changeable) title."""
        return f"Port {self.port_number} {self._suffix}".strip()
