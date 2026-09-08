"""Tests for the config and options flows."""

from __future__ import annotations

from datetime import timedelta

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gamescare.const import CONF_SCAN_INTERVAL, DOMAIN

from .conftest import HOST, FakeSwitch


async def test_user_flow_happy_path(hass: HomeAssistant, fake_switch: FakeSwitch) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: f"http://{HOST}/"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "gcswitch"
    assert result["data"] == {CONF_HOST: HOST}
    assert result["result"].unique_id == HOST
    assert len(fake_switch.calls_for("GET", "settings")) >= 1


async def test_user_flow_cannot_connect_then_recover(
    hass: HomeAssistant, fake_switch: FakeSwitch
) -> None:
    fake_switch.offline = True
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    fake_switch.offline = False
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_invalid_response(hass: HomeAssistant, fake_switch: FakeSwitch) -> None:
    fake_switch.settings = {"foo": "bar"}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_response"}


async def test_user_flow_empty_host(hass: HomeAssistant, fake_switch: FakeSwitch) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "http://"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert fake_switch.calls == []


async def test_user_flow_already_configured(
    hass: HomeAssistant, fake_switch: FakeSwitch, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST.upper()}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_interval(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    entry = init_integration
    assert entry.runtime_data.update_interval == timedelta(seconds=15)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 42}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SCAN_INTERVAL: 42}
    # The update listener reloads the entry so the new interval takes effect.
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert entry.runtime_data.update_interval == timedelta(seconds=42)
