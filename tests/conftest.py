"""Shared fixtures: a stateful fake switch served through aioresponses."""

from __future__ import annotations

from collections.abc import Generator
from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any

import aiohttp
from aioresponses import CallbackResult, aioresponses
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.gamescare.const import CONF_SCAN_INTERVAL, DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "192.168.1.226"
BASE_URL = f"http://{HOST}/"
PORTS_RE = re.compile(rf"^{re.escape(BASE_URL)}ports(\?.*)?$")
SETTINGS_RE = re.compile(rf"^{re.escape(BASE_URL)}settings(\?.*)?$")


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in every test."""


@pytest.fixture
def ports_payload() -> dict[str, Any]:
    return load_fixture("ports.json")


@pytest.fixture
def settings_payload() -> dict[str, Any]:
    return load_fixture("settings.json")


@pytest.fixture
def mock_api() -> Generator[aioresponses]:
    # Pass through requests to Home Assistant's own test HTTP server (hass_client).
    with aioresponses(passthrough=["http://127.0.0.1", "http://localhost"]) as mocked:
        yield mocked


class FakeSwitch:
    """A minimal in-memory model of the device's HTTP API."""

    def __init__(
        self,
        mocked: aioresponses,
        ports: dict[str, Any],
        settings: dict[str, Any],
    ) -> None:
        self.ports = deepcopy(ports)
        self.settings = deepcopy(settings)
        self.calls: list[tuple[str, URL, dict[str, Any] | None]] = []
        self.offline = False
        self.http_status = 200
        self.garbage = False
        self.drop_on_reboot = False
        mocked.get(PORTS_RE, callback=self._get_ports, repeat=True)
        mocked.post(PORTS_RE, callback=self._post_ports, repeat=True)
        mocked.get(SETTINGS_RE, callback=self._get_settings, repeat=True)
        mocked.post(SETTINGS_RE, callback=self._post_settings, repeat=True)

    # -- helpers -----------------------------------------------------------

    def calls_for(self, method: str, path: str) -> list[tuple[str, URL, dict[str, Any] | None]]:
        return [c for c in self.calls if c[0] == method and c[1].path == f"/{path}"]

    def _record(self, method: str, url: URL, kwargs: dict[str, Any]) -> None:
        self.calls.append((method, url, kwargs.get("data")))
        if self.offline:
            msg = "offline"
            raise aiohttp.ClientConnectionError(msg)

    def _reply(self, payload: dict[str, Any]) -> CallbackResult:
        if self.garbage:
            return CallbackResult(status=200, body="<html>not json</html>")
        return CallbackResult(status=self.http_status, payload=deepcopy(payload))

    # -- endpoints ---------------------------------------------------------

    def _get_ports(self, url: URL, **kwargs: Any) -> CallbackResult:
        self._record("GET", url, kwargs)
        if "force" in url.query:
            number = int(url.query["force"])
            self.ports["active"] = number
            self.ports["forced"] = 1 if number else 0
        return self._reply(self.ports)

    def _post_ports(self, url: URL, **kwargs: Any) -> CallbackResult:
        self._record("POST", url, kwargs)
        form: dict[str, str] = kwargs.get("data") or {}
        port = self.ports["ports"][int(form["port"]) - 1]
        if "title" in form:
            port["title"] = form["title"]
        if form.get("resetplaytime") == "true":
            port["playtime"] = 0
        if "outputmode" in form:
            port["outputmode"] = int(form["outputmode"])
        return self._reply(self.ports)

    def _get_settings(self, url: URL, **kwargs: Any) -> CallbackResult:
        self._record("GET", url, kwargs)
        if "reboot" in url.query and self.drop_on_reboot:
            msg = "connection dropped"
            raise aiohttp.ServerDisconnectedError(msg)
        return self._reply(self.settings)

    def _post_settings(self, url: URL, **kwargs: Any) -> CallbackResult:
        self._record("POST", url, kwargs)
        form: dict[str, str] = kwargs.get("data") or {}
        if "backlight" in form:
            self.settings["backlight"] = int(form["backlight"])
        return self._reply(self.settings)


@pytest.fixture
def fake_switch(
    mock_api: aioresponses,
    ports_payload: dict[str, Any],
    settings_payload: dict[str, Any],
) -> FakeSwitch:
    return FakeSwitch(mock_api, ports_payload, settings_payload)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="gcswitch",
        data={CONF_HOST: HOST},
        options={CONF_SCAN_INTERVAL: 15},
        unique_id=HOST,
        entry_id="gamescare_test_entry",
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    fake_switch: FakeSwitch,
) -> MockConfigEntry:
    """Set up the integration against the fake switch."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
