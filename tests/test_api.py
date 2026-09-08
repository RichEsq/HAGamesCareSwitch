"""Tests for the HA-free API client."""

from __future__ import annotations

from typing import Any

import aiohttp
from aioresponses import aioresponses
import pytest

from custom_components.gamescare.api import (
    GamesCareApiError,
    GamesCareClient,
    GamesCareConnectionError,
    PortsState,
    Settings,
    normalise_host,
)

from .conftest import BASE_URL, HOST, FakeSwitch


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def client(session: aiohttp.ClientSession) -> GamesCareClient:
    return GamesCareClient(HOST, session)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("192.168.1.226", "192.168.1.226"),
        (" 192.168.1.226 ", "192.168.1.226"),
        ("http://192.168.1.226/", "192.168.1.226"),
        ("HTTP://GCSwitch.local/ports", "gcswitch.local"),
        ("https://gcswitch:8080", "gcswitch:8080"),
        ("", ""),
    ],
)
def test_normalise_host(raw: str, expected: str) -> None:
    assert normalise_host(raw) == expected


def test_client_urls(client: GamesCareClient) -> None:
    assert client.host == HOST
    assert client.base_url == BASE_URL


def test_ports_state_from_fixture(ports_payload: dict[str, Any]) -> None:
    state = PortsState.from_json(ports_payload)
    assert state.port_count == 8
    assert state.active == 8
    assert state.forced is True
    first = state.ports[0]
    assert first.number == 1
    assert first.title == ""
    assert first.display_name == "Port 1"
    assert first.playtime == 5
    assert first.detected is False
    assert first.outputmode == 0
    assert first.ossc_profile == -1
    assert state.ports[7].detected is True
    assert state.get_port(8) is state.ports[7]
    assert state.get_port(0) is None
    assert state.get_port(9) is None


def test_ports_state_tolerates_missing_fields() -> None:
    state = PortsState.from_json({"ports": [{"title": "Saturn"}, None], "active": "2", "forced": 0})
    assert state.port_count == 2
    assert state.ports[0].display_name == "Saturn"
    assert state.ports[0].outputmode is None
    assert state.ports[1].title == ""
    assert state.active == 2
    assert state.forced is False


@pytest.mark.parametrize("payload", [None, [], {}, {"ports": "nope"}])
def test_ports_state_rejects_garbage(payload: Any) -> None:
    with pytest.raises(GamesCareApiError):
        PortsState.from_json(payload)


def test_settings_from_fixture(settings_payload: dict[str, Any]) -> None:
    settings = Settings.from_json(settings_payload)
    assert settings.version == "3.1.2"
    assert settings.hostname == "gcswitch"
    assert settings.boards == 1
    assert settings.port_count == 8
    assert settings.backlight is True
    assert settings.has_output_mode is True
    assert settings.has_retrotink is False
    assert settings.ssid == "Ranche-IoT"


def test_settings_rejects_garbage() -> None:
    with pytest.raises(GamesCareApiError):
        Settings.from_json({"foo": "bar"})


async def test_get_ports_and_settings(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    ports = await client.get_ports()
    assert ports.active == 8
    settings = await client.get_settings()
    assert settings.version == "3.1.2"
    assert len(fake_switch.calls_for("GET", "ports")) == 1
    assert len(fake_switch.calls_for("GET", "settings")) == 1


async def test_force_port(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    state = await client.force_port(3)
    assert state.active == 3
    assert state.forced is True
    state = await client.force_port(0)
    assert state.active == 0
    assert state.forced is False
    urls = [call[1] for call in fake_switch.calls_for("GET", "ports")]
    assert urls[0].query["force"] == "3"
    assert urls[1].query["force"] == "0"


async def test_force_port_rejects_negative(client: GamesCareClient) -> None:
    with pytest.raises(ValueError, match="Port number"):
        await client.force_port(-1)


async def test_update_port_sends_form(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    state = await client.update_port(
        2,
        title="Saturn",
        outputmode=1,
        reset_playtime=True,
        gbs_slot="a",
        rt_profile=4,
        ossc_profile=2,
        pixelfx_preset="/p",
    )
    assert state.ports[1].title == "Saturn"
    (call,) = fake_switch.calls_for("POST", "ports")
    assert call[2] == {
        "port": "2",
        "title": "Saturn",
        "outputmode": "1",
        "resetplaytime": "true",
        "gbs_slot": "a",
        "rt_profile": "4",
        "ossc_profile": "2",
        "pixelfx_preset": "/p",
    }


async def test_update_port_omits_unset_fields(
    client: GamesCareClient, fake_switch: FakeSwitch
) -> None:
    await client.update_port(1, title="")
    (call,) = fake_switch.calls_for("POST", "ports")
    assert call[2] == {"port": "1", "title": ""}


async def test_update_port_validation(client: GamesCareClient) -> None:
    with pytest.raises(ValueError, match="1-based"):
        await client.update_port(0, title="x")
    with pytest.raises(ValueError, match="16 characters"):
        await client.update_port(1, title="x" * 17)


async def test_set_backlight_and_reboot(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    await client.set_backlight(on=False)
    await client.set_backlight(on=True)
    posts = fake_switch.calls_for("POST", "settings")
    assert [c[2] for c in posts] == [{"backlight": "0"}, {"backlight": "1"}]
    await client.reboot()
    (call,) = fake_switch.calls_for("GET", "settings")
    assert call[1].query["reboot"] == "1"


async def test_http_error(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    fake_switch.http_status = 500
    with pytest.raises(GamesCareApiError, match="HTTP 500"):
        await client.get_ports()


async def test_invalid_json(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    fake_switch.garbage = True
    with pytest.raises(GamesCareApiError, match="invalid JSON"):
        await client.get_settings()


async def test_connection_error(client: GamesCareClient, fake_switch: FakeSwitch) -> None:
    fake_switch.offline = True
    with pytest.raises(GamesCareConnectionError):
        await client.get_ports()


async def test_timeout(client: GamesCareClient, mock_api: aioresponses) -> None:
    mock_api.get(f"{BASE_URL}ports", exception=TimeoutError())
    with pytest.raises(GamesCareConnectionError, match="Timeout"):
        await client.get_ports()
