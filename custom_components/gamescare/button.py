"""Button platform: reboot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory

from .entity import GamesCareEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import GamesCareConfigEntry, GamesCareCoordinator


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GamesCareConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the reboot button."""
    async_add_entities([GamesCareRebootButton(entry.runtime_data)])


class GamesCareRebootButton(GamesCareEntity, ButtonEntity):
    """Reboot the switch."""

    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GamesCareCoordinator) -> None:
        """Initialise the button."""
        super().__init__(coordinator, "reboot")

    async def async_press(self) -> None:
        """Reboot the device."""
        await self.coordinator.async_reboot()
