"""Constants for idm_heatpump."""

from enum import EnumMeta, IntEnum, IntFlag
from typing import Any


class SensorFeatures(IntFlag):
    """Possible features for sensors."""

    NONE = 0
    SET_POWER = 1
    SET_BATTERY = 2
    SET_TEMPERATURE = 4
    SET_HUMIDITY = 8
    SET_ROOM_MODE = 16
    SET_BINARY = 32
    SET_SYSTEM_STATUS = 64


class _CaseInsensitiveEnumMeta(EnumMeta):
    def __getitem__(cls, item):
        if isinstance(item, str):
            item = item.upper()
        return super().__getitem__(item)


class _SensorEnum(IntEnum, metaclass=_CaseInsensitiveEnumMeta):
    def __str__(self) -> str:
        return self.name.lower()


class _SensorFlag(IntFlag, metaclass=_CaseInsensitiveEnumMeta):
    def __str__(self) -> str:
        return ", ".join([f.name.lower() for f in self])


class HeatPumpStatus(_SensorFlag):
    """Status flags for heat pump."""

    OFF = 0
    HEATING = 1
    COOLING = 2
    WATER = 4
    DEFROSTING = 8

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.OFF if value is None else None


class IscMode(_SensorFlag):
    """ISC mode flags."""

    NONE = 0
    HEATING = 1
    WATER = 4
    SOURCE = 8

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.NONE if value is None else None


class CircuitMode(_SensorEnum):
    """Operating mode of heating circuit."""

    OFF = 0
    TIMED = 1
    NORMAL = 2
    ECO = 3
    MANUAL_HEAT = 4
    MANUAL_COOL = 5

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.OFF if value is None else None


class ActiveCircuitMode(_SensorEnum):
    """Active operation mode of heating circuit."""

    OFF = 0
    HEATING = 1
    COOLING = 2

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.OFF if value is None else None


class ZoneMode(_SensorEnum):
    """Zone operation mode."""

    COOLING = 0
    HEATING = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.HEATING if value is None else None


class RoomMode(_SensorEnum):
    """Room operation mode."""

    OFF = 0
    AUTOMATIC = 1
    ECO = 2
    NORMAL = 3
    COMFORT = 4

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.OFF if value is None else None


class SystemStatus(_SensorEnum):
    """IDM heat pump system status."""

    STANDBY = 0
    AUTOMATIC = 1
    AWAY = 2
    HOLIDAY = 3
    HOT_WATER_ONLY = 4
    HEATING_COOLING_ONLY = 5

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.STANDBY if value is None else None


class SmartGridStatus(_SensorEnum):
    """Smart grid status."""

    GRID_BLOCKED_SOLAR_OFF = 0
    GRID_ALLOWED_SOLAR_OFF = 1
    GRID_UNUSED_SOLAR_ON = 2
    GRID_BLOCKED_SOLAR_ON = 4

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.GRID_BLOCKED_SOLAR_OFF if value is None else None


class SolarMode(_SensorEnum):
    """Solar mode."""

    AUTO = 0
    WATER = 1
    HEATING = 2
    WATER_HEATING = 3
    SOURCE_POOL = 4

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.AUTO if value is None else None


class ValveStateHeatingCooling(_SensorEnum):
    """Valve state switching between heating and cooling."""

    HEATING = 0
    COOLING = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.HEATING if value is None else None


class ValveStateHeatingWater(_SensorEnum):
    """Valve state switching between heating and hot water."""

    HEATING = 0
    HOT_WATER = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.HEATING if value is None else None


class ValveStateStorageHeatSource(_SensorEnum):
    """Valve state switching between storage and heat source."""

    STORAGE = 0
    HEAT_SOURCE = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.STORAGE if value is None else None


class ValveStateHeatSourceColdStorage(_SensorEnum):
    """Valve state switching between heat source and cold storage."""

    HEAT_SOURCE = 0
    COLD_STORAGE = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.HEAT_SOURCE if value is None else None


class ValveStateStorageBypass(_SensorEnum):
    """Valve state switching between storage and bypass."""

    STORAGE = 0
    BYPASS = 1

    @classmethod
    def _missing_(cls, value) -> Any:
        return cls.STORAGE if value is None else None


# Base component constants
NAME = "IDM Heat Pump"
MANUFACTURER = "IDM"
MODEL_MAIN = "Navigator 2.0"
MODEL_ZONE = "Navigator Pro Einzelraumregelung"
DOMAIN = "idm_heatpump"
DOMAIN_DATA = f"{DOMAIN}_data"
ISSUE_URL = "https://github.com/kodebach/hacs-idm-heatpump/issues"

# Services
SERVICE_SET_POWER = "set_power"
SERVICE_SET_BATTERY = "set_battery"
SERVICE_SET_TEMPERATURE = "set_temperature"
SERVICE_SET_HUMIDITY = "set_humidity"
SERVICE_SET_ROOM_MODE = "set_room_mode"
SERVICE_SET_BINARY = "set_binary"
SERVICE_SET_SYSTEM_STATUS = "set_system_status"

# Limits
MIN_REFRESH_INTERVAL = {"hours": 0, "minutes": 1, "seconds": 0}
MAX_ZONE_COUNT = 10
MAX_ROOM_COUNT = 8

# Configuration and options
CONF_ENABLED = "enabled"
CONF_HOSTNAME = "hostname"
CONF_DISPLAY_NAME = "display_name"

OPT_REFRESH_INTERVAL = "refresh_interval"
OPT_REQUEST_TIMEOUT = "request_timeout"
OPT_HEATING_CIRCUITS = "heating_circuits"
OPT_ZONE_COUNT = "zone_count"
OPT_ZONE_ROOM_COUNT = [f"zone_{i}_room_count" for i in range(MAX_ZONE_COUNT)]
OPT_ZONE_ROOM_9_RELAY = [f"zone_{i}_room_9_relay" for i in range(MAX_ZONE_COUNT)]
OPT_READ_WITHOUT_GROUPS = "read_without_groups"
OPT_MAX_POWER_USAGE = "max_power_usage"

NAME_POWER_USAGE = "power_current_draw"

# Defaults
DEFAULT_NAME = DOMAIN
DEFAULT_REFRESH_INTERVAL = {"hours": 0, "minutes": 5, "seconds": 0}
DEFAULT_REQUEST_TIMEOUT = {"hours": 0, "minutes": 0, "seconds": 30}

STARTUP_MESSAGE_TEMPLATE = """
-------------------------------------------------------------------
%s
Version: %s
This is a custom integration!
If you have any issues with this you need to open an issue here:
%s
-------------------------------------------------------------------
"""
