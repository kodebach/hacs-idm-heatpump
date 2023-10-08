"""Constants for idm_heatpump."""

from homeassistant.const import Platform

# Base component constants
NAME = "IDM Heat Pump"
MANUFACTURER = "IDM"
MODEL_MAIN = "Navigator 2.0"
MODEL_ZONE = "Navigator Pro Einzelraumregelung"
DOMAIN = "idm_heatpump"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/kodebach/hacs-idm-heatpump/issues"

# Platforms
BINARY_SENSOR = Platform.BINARY_SENSOR
SENSOR = Platform.SENSOR
PLATFORMS = [BINARY_SENSOR, SENSOR]

# Limits
MIN_REFRESH_INTERVAL = {"hours": 0, "minutes": 1, "seconds": 0}
MAX_ZONE_COUNT = 10
MAX_ROOM_COUNT = 8

# Configuration and options
CONF_ENABLED = "enabled"
CONF_HOSTNAME = "hostname"
CONF_DISPLAY_NAME = "display_name"

OPT_REFRESH_INTERVAL = "refresh_interval"
OPT_HEATING_CIRCUITS = "heating_circuits"
OPT_ZONE_COUNT = "zone_count"
OPT_ZONE_ROOM_COUNT = [f"zone_{i}_room_count" for i in range(MAX_ZONE_COUNT)]
OPT_ZONE_ROOM_9_RELAY = [
    f"zone_{i}_room_9_relay" for i in range(MAX_ZONE_COUNT)]

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_REFRESH_INTERVAL = {"hours": 0, "minutes": 5, "seconds": 0}


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
