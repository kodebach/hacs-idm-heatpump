"""Constants for idm_heatpump."""

from enum import IntFlag, IntEnum
from homeassistant.const import Platform


class SensorFeatures(IntFlag):
    """Possible features for sensors."""

    NONE = 0
    SET_POWER = 1


class _SensorEnum(IntEnum):
    def __str__(self) -> str:
        return self.name.lower()


class _SensorFlag(IntFlag):
    def __str__(self) -> str:
        return ", ".join([f.name.lower() for f in self])


class HeatPumpStatus(_SensorFlag):
    """Status flags for heat pump."""

    OFF = 0
    HEATING = 1
    COOLING = 2
    WATER = 4
    DEFROSTING = 8


class IscMode(_SensorFlag):
    """ISC mode flags."""

    NONE = 0
    HEATING = 1
    WATER = 4
    SOURCE = 8


class CircuitMode(_SensorEnum):
    """Operating mode of heating circuit."""

    OFF = 0
    TIMED = 1
    NORMAL = 2
    ECO = 3
    MANUAL_HEAT = 4
    MANUAL_COOL = 5


class ActiveCircuitMode(_SensorEnum):
    """Active operation mode of heating circuit."""

    OFF = 0
    HEATING = 1
    COOLING = 2


class ZoneMode(_SensorEnum):
    """Zone operation mode."""

    COOLING = 0
    HEATING = 1


class RoomMode(_SensorEnum):
    """Room operation mode."""

    OFF = 0
    AUTOMATIC = 1
    ECO = 2
    NORMAL = 3
    COMFORT = 4


class SystemStatus(_SensorEnum):
    """IDM heat pump system status."""

    STANDBY = 0
    AUTOMATIC = 1
    AWAY = 2
    HOT_WATER_ONLY = 4
    HEATING_COOLING_ONLY = 5


class SmartGridStatus(_SensorEnum):
    """Smart grid status."""

    GRID_BLOCKED_SOLAR_OFF = 0
    GRID_ALLOWED_SOLAR_OFF = 1
    GRID_UNUSED_SOLAR_ON = 2
    GRID_BLOCKED_SOLAR_ON = 4


class SolarMode(_SensorEnum):
    """Solar mode."""

    AUTO = 0
    WATER = 1
    HEATING = 2
    WATER_HEATING = 3
    SOURCE_POOL = 4


# Base component constants
NAME = "IDM Heat Pump"
MANUFACTURER = "IDM"
MODEL_MAIN = "Navigator 2.0"
MODEL_ZONE = "Navigator Pro Einzelraumregelung"
DOMAIN = "idm_heatpump"
DOMAIN_DATA = f"{DOMAIN}_data"
ISSUE_URL = "https://github.com/kodebach/hacs-idm-heatpump/issues"

# Platforms
BINARY_SENSOR = Platform.BINARY_SENSOR
SENSOR = Platform.SENSOR
PLATFORMS = [BINARY_SENSOR, SENSOR]

# Services
SERVICE_SET_POWER = "set_power"

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
OPT_ZONE_ROOM_9_RELAY = [f"zone_{i}_room_9_relay" for i in range(MAX_ZONE_COUNT)]

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_REFRESH_INTERVAL = {"hours": 0, "minutes": 5, "seconds": 0}

STARTUP_MESSAGE_TEMPLATE = """
-------------------------------------------------------------------
%s
Version: %s
This is a custom integration!
If you have any issues with this you need to open an issue here:
%s
-------------------------------------------------------------------
"""
