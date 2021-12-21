"""Constants for idm_heatpump."""
# Base component constants
NAME = "IDM Heat Pump"
MANUFACTURER = "IDM"
DOMAIN = "idm_heatpump"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/kodebach/hacs-idm-heatpump/issues"

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
PLATFORMS = [BINARY_SENSOR, SENSOR]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_HOSTNAME = "hostname"
CONF_DISPLAY_NAME = "display_name"

OPT_REFRESH_INTERVAL = "refresh_interval"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
