# GamesCare RGB Switch for Home Assistant

[![CI](https://github.com/RichEsq/HAGamesCareSwitch/actions/workflows/ci.yml/badge.svg)](https://github.com/RichEsq/HAGamesCareSwitch/actions/workflows/ci.yml)
[![Validate](https://github.com/RichEsq/HAGamesCareSwitch/actions/workflows/validate.yml/badge.svg)](https://github.com/RichEsq/HAGamesCareSwitch/actions/workflows/validate.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration that controls and monitors a
[GamesCare RGB (SCART) Switch](https://gamescare.com.br/) over its local HTTP API.

- Pick the active input (or hand control back to auto-detect) from a `select` entity.
- Get a `binary_sensor` per port that turns on when the switch sees sync on that input. This
  is the useful automation trigger: "the Saturn was powered on".
- Track per-port playtime, toggle the backlight and reboot the unit.
- Rename ports and reset playtime counters through services.

Everything is local polling. No cloud, no account, no authentication.

<!-- TODO: screenshot of the device page. Drop it in docs/screenshot.png and uncomment. -->
<!-- ![GamesCare RGB Switch device page in Home Assistant](docs/screenshot.png) -->


## Requirements

- A GamesCare RGB Switch running firmware 3.1.x (developed and verified against 3.1.2).
- The switch must be joined to your WiFi network in **client mode** and reachable from Home
  Assistant over HTTP on port 80.
- Home Assistant 2025.12 or newer.

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/RichEsq/HAGamesCareSwitch` with category **Integration**.
3. Search for **GamesCare RGB Switch** in HACS and download it.
4. Restart Home Assistant.

### Manual

Download `gamescare.zip` from the
[latest release](https://github.com/RichEsq/HAGamesCareSwitch/releases/latest), extract it into
`<config>/custom_components/gamescare/` and restart Home Assistant.

## Configuration

### 1. Put the switch on your network

Out of the box the switch runs its own access point with a captive portal. Connect to that access
point, open the portal (the switch's own web page), and configure it to join your WiFi as a
client. See the vendor's documentation for the step-by-step: <https://gamescare.com.br/>.

Give the switch a DHCP reservation (or a static IP). The device exposes no serial number or MAC
address in its API, so the integration identifies it by host. **If the IP changes and you did not
use a hostname, Home Assistant will treat it as a new device.** Using the device's hostname
(default `gcswitch`, so `gcswitch.local` or `gcswitch` depending on your resolver) avoids this.

### 2. Add the integration

1. Go to **Settings > Devices & services > Add integration**.
2. Search for **GamesCare RGB Switch**.
3. Enter the IP address or hostname of the switch.

The integration validates the connection by reading the switch's settings and names the device
after the switch's hostname.

### Options

Open the integration's **Configure** dialog to change the poll interval (5 to 300 seconds,
default 15). The switch has no push mechanism, so this is how fast Home Assistant notices a
console powering on.

## Entities

All entities belong to one device (manufacturer GamesCare, model RGB Switch, firmware version
from the switch). Entity ids below assume the default hostname `gcswitch` and use `N` for the
1-based port number.

| Entity | Description |
| --- | --- |
| `select.gcswitch_input` | The main control. Options are `Auto`, `Port 1` ... `Port N`. Selecting a port forces it; `Auto` returns the switch to auto-detect. Attributes: `active_port`, `forced`, `port_titles`. |
| `binary_sensor.gcswitch_port_N_signal` | On when the switch detects sync on that input (device class connectivity). Attributes: `port`, `title`. |
| `binary_sensor.gcswitch_auto_mode` | On when no port is forced. Diagnostic. |
| `sensor.gcswitch_active_port` | Number of the currently selected port, 0 when none. Diagnostic. |
| `sensor.gcswitch_port_N_playtime` | Accumulated seconds that port has been active (duration, total increasing). Diagnostic and **disabled by default**; enable the ones you want. |
| `switch.gcswitch_backlight` | Front-panel backlight. Config. |
| `button.gcswitch_reboot` | Reboots the switch. Config. |

### Port names

Ports can be given a title (up to 16 characters) on the switch itself or with the
`gamescare.set_port_title` service. The **entity id stays `port_N`** so automations never break,
while the **friendly name follows the title**: port 3 titled `Saturn` shows up as
"gcswitch Saturn signal" at `binary_sensor.gcswitch_port_3_signal`.

The select's options are deliberately the stable strings `Port N` rather than the titles, so
renaming a port never changes the option list. The titles are available on the select through
the `port_titles` attribute.

## Services

| Service | Fields | Description |
| --- | --- | --- |
| `gamescare.set_port_title` | `device_id`, `port` (1-based), `title` (max 16 chars) | Renames a port. Pass an empty title to clear it. |
| `gamescare.reset_playtime` | `device_id`, `port` (1-based) | Resets the port's playtime counter to zero. |

## Example automations

A script per console for manual selection:

```yaml
script:
  play_saturn:
    sequence:
      - action: select.select_option
        target:
          entity_id: select.gcswitch_input
        data:
          option: "Port 3"
      # then set your HDMI switch input and scaler profile via other integrations
```

Leave the switch on `Auto` and let Home Assistant react when a console powers on:

```yaml
automation:
  - alias: Saturn powered on
    triggers:
      - trigger: state
        entity_id: binary_sensor.gcswitch_port_3_signal
        to: "on"
    actions:
      - action: script.set_scaler_saturn
```

Rename a port from a script:

```yaml
- action: gamescare.set_port_title
  data:
    device_id: !input gamescare_device
    port: 3
    title: Saturn
```

## Not in scope (v1)

- WiFi mode, SSID and password changes. A mistake there takes the switch off the network, so
  the integration never writes those fields. Use the switch's own web page.
- OTA firmware updates.
- Configuring the GBS-Control, RetroTINK, OSSC or PixelFX scaler integrations. The switch
  handles those itself; the per-port profile fields are parsed but not exposed or writable.
- mDNS discovery. Not yet verified against the device; add the switch by host.

## Device API notes

Reverse-engineered from the firmware 3.1.2 web UI and verified against a live unit. The vendor
PDF is out of date where it conflicts with this table. Base URL is `http://<host>/`, all
responses are JSON, and port numbers are 1-based everywhere.

| Endpoint | Purpose |
| --- | --- |
| `GET /ports` | State. Returns `ports[]` (`title`, `playtime`, `detected`, `outputmode`, `gbs_slot`, `rt_profile`, `ossc_profile`, `pixelfx_preset`), `active` (0 = none) and `forced` (0/1). Port count is the array length (`settings.boards * 8`). |
| `GET /ports?force=N` | Select port `N` and set `forced=1`. `N=0` returns to auto-detect (`forced=0`, `active=0` until sync is seen). Returns the full `/ports` JSON. |
| `POST /ports` | Edit a port (form data). `port` is required; `title` (max 16), `outputmode`, `resetplaytime` (`true`/`false`), `gbs_slot`, `rt_profile`, `ossc_profile`, `pixelfx_preset` are optional and unchanged if omitted. Returns the full `/ports` JSON. |
| `GET /settings` | Configuration: `mode` (1 AP + portal, 2 AP, 3 client), `language`, `boards`, `backlight` (0/1), `address`, `hostname`, `version`, scaler flags, `has_retrotink`, `has_ir`, `has_output_mode`, `has_expansion`, `theme_color`, `ssid`. |
| `POST /settings` | Write configuration (form data, omitted fields unchanged). The integration only ever sends `backlight`. |
| `GET /settings?reboot=1` | Reboot. |
| `GET /settings?networks=1` | As `/settings` plus `wifi`, a tab-separated list of SSIDs in range. Not used. |
| `GET /pixelfx`, `GET /gbs`, `GET /update?status=1`, `POST /update`, `POST /update-file` | Scaler and OTA endpoints. Not used. |

Behaviour notes:

- No push. The web UI reads `/ports` and `/settings` once and only refetches after an action.
  The integration polls `/ports` every interval and `/settings` every 5 minutes, and pushes the
  JSON returned by writes straight into Home Assistant rather than waiting for the next poll.
- Requests complete well under a second on a LAN; the client uses a 5 second timeout.
- The old `autodetect` field in the vendor PDF no longer exists in this firmware.

## Development

```sh
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
ruff check . && ruff format --check . && mypy
pytest
```

Tests run against a fake switch served through `aioresponses`; the fixture payloads under
`tests/fixtures/` are the verbatim responses from a real unit. The `api.py` module has no Home
Assistant imports so it can be split into a standalone package later.

Releases are cut by pushing a `vX.Y.Z` tag that matches `manifest.json`; the release workflow
builds `gamescare.zip` and attaches it to the GitHub release for HACS.

## Licence

[MIT](LICENSE)
