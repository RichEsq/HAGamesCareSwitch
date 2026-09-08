"""Switch platform: front-panel backlight."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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
    """Set up the backlight switch."""
    async_add_entities([GamesCareBacklightSwitch(entry.runtime_data)])


class GamesCareBacklightSwitch(GamesCareEntity, SwitchEntity):
    """Turn the switch's backlight on or off."""

    _attr_translation_key = "backlight"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: GamesCareCoordinator) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, "backlight")

    @property
    def is_on(self) -> bool:
        """Return True when the backlight is on."""
        return self.coordinator.data.settings.backlight

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the backlight on."""
        await self.coordinator.async_set_backlight(on=True)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn the backlight off."""
        await self.coordinator.async_set_backlight(on=False)
