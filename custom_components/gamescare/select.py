"""Select platform: the main input selector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import ServiceValidationError

from .const import (
    ATTR_ACTIVE_PORT,
    ATTR_FORCED,
    ATTR_PORT_TITLES,
    DOMAIN,
    OPTION_AUTO,
    PORT_OPTION_PREFIX,
)
from .entity import GamesCareEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import GamesCareConfigEntry, GamesCareCoordinator


def port_option(number: int) -> str:
    """Return the select option string for a 1-based port number."""
    return f"{PORT_OPTION_PREFIX}{number}"


def option_to_port(option: str) -> int | None:
    """Return the port number for an option (0 for Auto), or None if invalid."""
    if option == OPTION_AUTO:
        return 0
    if option.startswith(PORT_OPTION_PREFIX):
        rest = option[len(PORT_OPTION_PREFIX) :]
        if rest.isdigit():
            return int(rest)
    return None


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: GamesCareConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the input select."""
    async_add_entities([GamesCareInputSelect(entry.runtime_data)])


class GamesCareInputSelect(GamesCareEntity, SelectEntity):
    """Select the active input port, or return to auto-detect.

    Options are the stable strings ``Auto``, ``Port 1`` ... ``Port N`` so that
    renaming a port does not churn the option list. The user-set titles are
    exposed through the ``port_titles`` attribute instead.
    """

    _attr_translation_key = "input"

    def __init__(self, coordinator: GamesCareCoordinator) -> None:
        """Initialise the select."""
        super().__init__(coordinator, "input")

    @property
    def options(self) -> list[str]:
        """Return ``Auto`` plus one option per port."""
        count = self.coordinator.data.ports.port_count
        return [OPTION_AUTO, *(port_option(n) for n in range(1, count + 1))]

    @property
    def current_option(self) -> str | None:
        """Return ``Auto`` in auto-detect mode, else the forced port."""
        state = self.coordinator.data.ports
        if not state.forced:
            return OPTION_AUTO
        if 1 <= state.active <= state.port_count:
            return port_option(state.active)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw active port, forced flag and port titles."""
        state = self.coordinator.data.ports
        return {
            ATTR_ACTIVE_PORT: state.active,
            ATTR_FORCED: state.forced,
            ATTR_PORT_TITLES: {port_option(p.number): p.title for p in state.ports},
        }

    async def async_select_option(self, option: str) -> None:
        """Force a port, or return to auto-detect mode."""
        number = option_to_port(option)
        if number is None or number > self.coordinator.data.ports.port_count:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_option",
                translation_placeholders={"option": option},
            )
        await self.coordinator.async_force_port(number)
