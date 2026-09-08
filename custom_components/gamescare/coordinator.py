"""Data update coordinator for the GamesCare RGB Switch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    GamesCareApiError,
    GamesCareClient,
    GamesCareConnectionError,
    GamesCareError,
    PortsState,
    Settings,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    SETTINGS_REFRESH_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

type GamesCareConfigEntry = ConfigEntry[GamesCareCoordinator]


@dataclass(frozen=True, slots=True)
class GamesCareData:
    """Combined device state held by the coordinator."""

    ports: PortsState
    settings: Settings


class GamesCareCoordinator(DataUpdateCoordinator[GamesCareData]):
    """Poll ``/ports`` every interval and ``/settings`` occasionally."""

    config_entry: GamesCareConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GamesCareConfigEntry,
        client: GamesCareClient,
    ) -> None:
        """Initialise the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {client.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._settings: Settings | None = None
        self._settings_fetched_at: datetime | None = None

    @property
    def host(self) -> str:
        """Return the device host."""
        return self.client.host

    def _settings_stale(self) -> bool:
        if self._settings is None or self._settings_fetched_at is None:
            return True
        age = dt_util.utcnow() - self._settings_fetched_at
        return age >= timedelta(seconds=SETTINGS_REFRESH_INTERVAL)

    async def _async_fetch_settings(self) -> Settings:
        settings = await self.client.get_settings()
        self._settings = settings
        self._settings_fetched_at = dt_util.utcnow()
        return settings

    async def _async_update_data(self) -> GamesCareData:
        """Fetch the latest state from the device."""
        try:
            if self._settings_stale():
                await self._async_fetch_settings()
            ports = await self.client.get_ports()
        except GamesCareConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"host": self.host, "error": str(err)},
            ) from err
        except GamesCareApiError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_response",
                translation_placeholders={"host": self.host, "error": str(err)},
            ) from err
        if TYPE_CHECKING:
            assert self._settings is not None
        return GamesCareData(ports=ports, settings=self._settings)

    def _push_ports(self, ports: PortsState) -> None:
        """Push a fresh ``/ports`` state returned by a write into the coordinator."""
        self.async_set_updated_data(GamesCareData(ports=ports, settings=self.data.settings))

    @staticmethod
    def _wrap(err: GamesCareError, host: str) -> HomeAssistantError:
        key = "cannot_connect" if isinstance(err, GamesCareConnectionError) else "invalid_response"
        return HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=key,
            translation_placeholders={"host": host, "error": str(err)},
        )

    async def async_force_port(self, number: int) -> None:
        """Select a port (``0`` for auto-detect) and push the returned state."""
        try:
            ports = await self.client.force_port(number)
        except GamesCareError as err:
            raise self._wrap(err, self.host) from err
        self._push_ports(ports)

    async def async_update_port(
        self,
        port: int,
        *,
        title: str | None = None,
        reset_playtime: bool = False,
    ) -> None:
        """Edit a port and push the returned state."""
        try:
            ports = await self.client.update_port(port, title=title, reset_playtime=reset_playtime)
        except GamesCareError as err:
            raise self._wrap(err, self.host) from err
        self._push_ports(ports)

    async def async_set_backlight(self, on: bool) -> None:  # noqa: FBT001
        """Set the backlight, then re-read settings so state reflects the device."""
        try:
            await self.client.set_backlight(on)
            settings = await self._async_fetch_settings()
        except GamesCareError as err:
            raise self._wrap(err, self.host) from err
        self.async_set_updated_data(GamesCareData(ports=self.data.ports, settings=settings))

    async def async_reboot(self) -> None:
        """Reboot the device.

        A dropped connection is expected here because the unit restarts before
        (or while) it answers, so connection errors are logged and swallowed.
        API errors are still raised.
        """
        try:
            await self.client.reboot()
        except GamesCareConnectionError as err:
            LOGGER.debug("Connection dropped while rebooting %s: %s", self.host, err)
        except GamesCareApiError as err:
            raise self._wrap(err, self.host) from err
