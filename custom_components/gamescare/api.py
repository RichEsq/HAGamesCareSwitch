"""Async HTTP client for the GamesCare RGB Switch local API.

This module deliberately has no Home Assistant imports so that it can be
split out into a standalone package later. The aiohttp session is injected.

The API was reverse-engineered from firmware 3.1.2's web UI. All endpoints are
plain unauthenticated HTTP on port 80 and return JSON. Port numbers are
1-based everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

DEFAULT_TIMEOUT = 5.0
MAX_TITLE_LENGTH = 16
PORTS_PER_BOARD = 8


class GamesCareError(Exception):
    """Base error for the GamesCare client."""


class GamesCareConnectionError(GamesCareError):
    """Raised when the device cannot be reached (network error or timeout)."""


class GamesCareApiError(GamesCareError):
    """Raised when the device answers with a non-200 status or bad JSON."""


def normalise_host(host: str) -> str:
    """Normalise a user-supplied host string.

    Strips whitespace, an optional ``http://`` or ``https://`` scheme, any
    trailing path and lower-cases the result so that the same device entered
    in different ways maps to the same identifier.
    """
    host = host.strip()
    for scheme in ("http://", "https://"):
        if host.lower().startswith(scheme):
            host = host[len(scheme) :]
            break
    host = host.split("/", 1)[0]
    return host.lower()


def _as_int(value: Any, default: int = 0) -> int:
    """Coerce a JSON value to int, tolerating strings and bools."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _as_bool(value: Any) -> bool:
    """Coerce a JSON value to bool, tolerating 0/1 ints and strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return False


def _as_str(value: Any) -> str:
    """Coerce a JSON value to str, mapping None to an empty string."""
    if value is None:
        return ""
    return str(value)


@dataclass(frozen=True, slots=True)
class Port:
    """State of a single input port."""

    number: int
    """1-based port number."""
    title: str
    playtime: int
    """Accumulated seconds this port has been active."""
    detected: bool
    """True when sync is currently detected on this input."""
    outputmode: int | None
    gbs_slot: str
    rt_profile: int
    ossc_profile: int
    pixelfx_preset: str

    @property
    def display_name(self) -> str:
        """Return the user-set title, or ``Port N`` when no title is set."""
        return self.title or f"Port {self.number}"

    @classmethod
    def from_json(cls, number: int, data: dict[str, Any]) -> Port:
        """Build a Port from one element of the ``/ports`` array."""
        outputmode = data.get("outputmode")
        return cls(
            number=number,
            title=_as_str(data.get("title")),
            playtime=_as_int(data.get("playtime")),
            detected=_as_bool(data.get("detected")),
            outputmode=None if outputmode is None else _as_int(outputmode),
            gbs_slot=_as_str(data.get("gbs_slot")),
            rt_profile=_as_int(data.get("rt_profile")),
            ossc_profile=_as_int(data.get("ossc_profile"), default=-1),
            pixelfx_preset=_as_str(data.get("pixelfx_preset")),
        )


@dataclass(frozen=True, slots=True)
class PortsState:
    """Parsed ``/ports`` response."""

    ports: tuple[Port, ...]
    active: int
    """Currently selected port, 0 when none is selected."""
    forced: bool
    """True when a port has been manually selected, False in auto-detect mode."""

    @property
    def port_count(self) -> int:
        """Return the number of ports the device reported."""
        return len(self.ports)

    def get_port(self, number: int) -> Port | None:
        """Return the port with the given 1-based number, if present."""
        if 1 <= number <= len(self.ports):
            return self.ports[number - 1]
        return None

    @classmethod
    def from_json(cls, data: Any) -> PortsState:
        """Build a PortsState from the ``/ports`` JSON payload."""
        if not isinstance(data, dict) or not isinstance(data.get("ports"), list):
            msg = "Unexpected /ports payload"
            raise GamesCareApiError(msg)
        raw_ports: list[Any] = data["ports"]
        ports = tuple(
            Port.from_json(index + 1, item if isinstance(item, dict) else {})
            for index, item in enumerate(raw_ports)
        )
        return cls(
            ports=ports,
            active=_as_int(data.get("active")),
            forced=_as_bool(data.get("forced")),
        )


@dataclass(frozen=True, slots=True)
class Settings:
    """Parsed ``/settings`` response."""

    mode: int
    """WiFi mode: 1 = AP + captive portal, 2 = AP, 3 = client."""
    language: int
    """0 = Portuguese, 1 = English."""
    boards: int
    """Number of boards installed, 8 ports each."""
    backlight: bool
    address: str
    hostname: str
    version: str
    """Firmware version string."""
    gbs_enabled: bool
    gbs_ip: str
    retrotink_enabled: bool
    ossc_enabled: bool
    pixelfx_enabled: bool
    pixelfx_ip: str
    pixelfx_pass_set: bool
    pixelfx_user: str
    has_retrotink: bool
    has_ir: bool
    has_output_mode: bool
    has_expansion: bool
    theme_color: str
    ssid: str

    @property
    def port_count(self) -> int:
        """Return the number of ports implied by the board count."""
        return self.boards * PORTS_PER_BOARD

    @classmethod
    def from_json(cls, data: Any) -> Settings:
        """Build a Settings from the ``/settings`` JSON payload."""
        if not isinstance(data, dict) or "version" not in data:
            msg = "Unexpected /settings payload"
            raise GamesCareApiError(msg)
        return cls(
            mode=_as_int(data.get("mode")),
            language=_as_int(data.get("language")),
            boards=max(_as_int(data.get("boards"), default=1), 1),
            backlight=_as_bool(data.get("backlight")),
            address=_as_str(data.get("address")),
            hostname=_as_str(data.get("hostname")),
            version=_as_str(data.get("version")),
            gbs_enabled=_as_bool(data.get("gbs_enabled")),
            gbs_ip=_as_str(data.get("gbs_ip")),
            retrotink_enabled=_as_bool(data.get("retrotink_enabled")),
            ossc_enabled=_as_bool(data.get("ossc_enabled")),
            pixelfx_enabled=_as_bool(data.get("pixelfx_enabled")),
            pixelfx_ip=_as_str(data.get("pixelfx_ip")),
            pixelfx_pass_set=_as_bool(data.get("pixelfx_pass_set")),
            pixelfx_user=_as_str(data.get("pixelfx_user")),
            has_retrotink=_as_bool(data.get("has_retrotink")),
            has_ir=_as_bool(data.get("has_ir")),
            has_output_mode=_as_bool(data.get("has_output_mode")),
            has_expansion=_as_bool(data.get("has_expansion")),
            theme_color=_as_str(data.get("theme_color")),
            ssid=_as_str(data.get("ssid")),
        )


def _form_bool(value: bool) -> str:  # noqa: FBT001
    """Encode a bool the way the device's web UI does."""
    return "true" if value else "false"


class GamesCareClient:
    """Thin async client for a GamesCare RGB Switch."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise the client.

        ``host`` is the IP address or hostname (optionally with ``:port``).
        ``session`` is an aiohttp session owned by the caller.
        """
        self._host = normalise_host(host)
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def host(self) -> str:
        """Return the normalised host."""
        return self._host

    @property
    def base_url(self) -> str:
        """Return the device's base URL."""
        return f"http://{self._host}/"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> Any:
        """Perform a request and return the decoded JSON body."""
        url = f"{self.base_url}{path.lstrip('/')}"
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                data=data,
                timeout=self._timeout,
            ) as response:
                if response.status != 200:  # noqa: PLR2004
                    msg = f"{method} {url} returned HTTP {response.status}"
                    raise GamesCareApiError(msg)
                try:
                    return await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as err:
                    msg = f"{method} {url} returned invalid JSON"
                    raise GamesCareApiError(msg) from err
        except TimeoutError as err:
            msg = f"Timeout talking to {url}"
            raise GamesCareConnectionError(msg) from err
        except aiohttp.ClientError as err:
            msg = f"Error talking to {url}: {err}"
            raise GamesCareConnectionError(msg) from err

    async def get_ports(self) -> PortsState:
        """Fetch ``/ports``."""
        return PortsState.from_json(await self._request("GET", "ports"))

    async def get_settings(self) -> Settings:
        """Fetch ``/settings``."""
        return Settings.from_json(await self._request("GET", "settings"))

    async def force_port(self, number: int) -> PortsState:
        """Select a port manually. ``0`` returns the unit to auto-detect mode.

        Returns the device's updated ``/ports`` state.
        """
        if number < 0:
            msg = "Port number must be 0 (auto) or a positive port number"
            raise ValueError(msg)
        return PortsState.from_json(
            await self._request("GET", "ports", params={"force": str(number)})
        )

    async def update_port(
        self,
        port: int,
        *,
        title: str | None = None,
        outputmode: int | None = None,
        reset_playtime: bool = False,
        gbs_slot: str | None = None,
        rt_profile: int | None = None,
        ossc_profile: int | None = None,
        pixelfx_preset: str | None = None,
    ) -> PortsState:
        """Edit a port. Omitted fields are left unchanged on the device.

        Returns the device's updated ``/ports`` state.
        """
        if port < 1:
            msg = "Port numbers are 1-based"
            raise ValueError(msg)
        form: dict[str, str] = {"port": str(port)}
        if title is not None:
            if len(title) > MAX_TITLE_LENGTH:
                msg = f"Title must be at most {MAX_TITLE_LENGTH} characters"
                raise ValueError(msg)
            form["title"] = title
        if outputmode is not None:
            form["outputmode"] = str(outputmode)
        if reset_playtime:
            form["resetplaytime"] = _form_bool(value=True)
        if gbs_slot is not None:
            form["gbs_slot"] = gbs_slot
        if rt_profile is not None:
            form["rt_profile"] = str(rt_profile)
        if ossc_profile is not None:
            form["ossc_profile"] = str(ossc_profile)
        if pixelfx_preset is not None:
            form["pixelfx_preset"] = pixelfx_preset
        return PortsState.from_json(await self._request("POST", "ports", data=form))

    async def set_backlight(self, on: bool) -> None:  # noqa: FBT001
        """Turn the front-panel backlight on or off."""
        await self._request("POST", "settings", data={"backlight": "1" if on else "0"})

    async def reboot(self) -> None:
        """Reboot the device.

        The unit may drop the connection before answering, in which case a
        ``GamesCareConnectionError`` is raised even though the reboot happened.
        """
        await self._request("GET", "settings", params={"reboot": "1"})


__all__ = [
    "DEFAULT_TIMEOUT",
    "MAX_TITLE_LENGTH",
    "PORTS_PER_BOARD",
    "GamesCareApiError",
    "GamesCareClient",
    "GamesCareConnectionError",
    "GamesCareError",
    "Port",
    "PortsState",
    "Settings",
    "normalise_host",
]
