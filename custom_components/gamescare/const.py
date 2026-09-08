"""Constants for the GamesCare RGB Switch integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "gamescare"
LOGGER = logging.getLogger(__package__)

MANUFACTURER: Final = "GamesCare"
MODEL: Final = "RGB Switch"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 15
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

# /settings barely changes, so it is only re-read this often (seconds).
SETTINGS_REFRESH_INTERVAL: Final = 300

OPTION_AUTO: Final = "Auto"
PORT_OPTION_PREFIX: Final = "Port "

ATTR_ACTIVE_PORT: Final = "active_port"
ATTR_FORCED: Final = "forced"
ATTR_PORT: Final = "port"
ATTR_PORT_TITLES: Final = "port_titles"
ATTR_TITLE: Final = "title"

SERVICE_SET_PORT_TITLE: Final = "set_port_title"
SERVICE_RESET_PLAYTIME: Final = "reset_playtime"
