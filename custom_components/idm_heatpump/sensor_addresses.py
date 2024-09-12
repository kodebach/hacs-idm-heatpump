"""Sensor addresses."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntEnum, IntFlag
from typing import Generic, TypeVar

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from .const import (
    CONF_DISPLAY_NAME,
    NAME_POWER_USAGE,
    ActiveCircuitMode,
    CircuitMode,
    HeatPumpStatus,
    IscMode,
    RoomMode,
    SensorFeatures,
    SmartGridStatus,
    SolarMode,
    SystemStatus,
    ValveStateHeatingCooling,
    ValveStateHeatingWater,
    ValveStateHeatSourceColdStorage,
    ValveStateStorageBypass,
    ValveStateStorageHeatSource,
    ZoneMode,
)
from .logger import LOGGER

_T = TypeVar("_T")
_EnumT = TypeVar("_EnumT", bound=IntEnum)
_FlagT = TypeVar("_FlagT", bound=IntFlag)


@dataclass(kw_only=True)
class BaseSensorAddress(ABC, Generic[_T]):
    """Base class for (binary) sensors of an IDM heatpump."""

    address: int
    name: str
    supported_features: SensorFeatures = SensorFeatures.NONE
    force_single: bool = False

    @property
    @abstractmethod
    def size(self) -> int:
        """Get number of registers this sensor's value occupies."""

    @abstractmethod
    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, _T]:
        """Decode this sensor's value."""

    @abstractmethod
    def encode(self, builder: BinaryPayloadBuilder, value: _T) -> None:
        """Encode this sensor's value."""

    @abstractmethod
    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        """Get SensorEntityDescription for this sensor."""

    @property
    def zone_id(self) -> int | None:
        """zero-based id of zone this sensors belongs to or None if it is a general sensor."""

        if self.address < 2000 or self.address > ZONE_OFFSETS[-1] + 65:
            return None

        for i, offset in enumerate(ZONE_OFFSETS):
            if offset > self.address:
                return i - 1

        return len(ZONE_OFFSETS)


@dataclass(kw_only=True)
class IdmSensorAddress(BaseSensorAddress[_T]):
    """Describes one of the sensors of an IDM heatpump."""

    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None


@dataclass(kw_only=True)
class IdmBinarySensorAddress(BaseSensorAddress[bool]):
    """Describes one of the binary sensors of an IDM heatpump."""

    device_class: BinarySensorDeviceClass | None = None

    @property
    def size(self) -> int:
        """Number of registers this sensor's value occupies."""
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, bool]:
        """Decode this sensor's value."""
        value = decoder.decode_16bit_uint()
        LOGGER.debug("raw value (uint16) for %s: %d", self.name, value)
        return (True, value > 0)

    def encode(self, builder: BinaryPayloadBuilder, value: bool):
        """Encode this sensor's value."""
        builder.add_16bit_uint(1 if value else 0)

    def entity_description(
        self, config_entry: ConfigEntry
    ) -> BinarySensorEntityDescription:
        """SensorEntityDescription for this sensor."""
        return BinarySensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
        )


@dataclass(kw_only=True)
class _FloatSensorAddress(IdmSensorAddress[float]):
    unit: str | None
    decimal_digits: int = 2
    scale: float = 1
    min_value: float | None = None
    max_value: float | None = None

    @property
    def size(self):
        return 2

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, float]:
        raw_value = decoder.decode_32bit_float()
        LOGGER.debug("raw value (float32) for %s: %d", self.name, raw_value)
        value = round(raw_value * self.scale, self.decimal_digits)
        LOGGER.debug("scaled & rounded value for %s: %d", self.name, value)

        if self.min_value == 0.0 and value == -1:
            # special case: unavailable
            return (False, 0.0)

        if (self.min_value is not None and value < self.min_value) or (
            self.max_value is not None and value > self.max_value
        ):
            raise ValueError(
                f"{value} out of range ({self.min_value} - {self.max_value})"
            )

        return (True, value)

    def encode(self, builder: BinaryPayloadBuilder, value: float):
        assert (self.min_value is None or value >= self.min_value) and (
            self.max_value is None or value <= self.max_value
        )
        builder.add_32bit_float(value)

    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass(kw_only=True)
class _UCharSensorAddress(IdmSensorAddress[int]):
    unit: str | None
    min_value: int | None = None
    max_value: int | None = 0xFFFE

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, int]:
        value = decoder.decode_16bit_uint()
        LOGGER.debug("raw value (uint16) for %s: %d", self.name, value)

        if self.max_value == 0xFFFE and value == 0xFFFF:
            # special case: unavailable
            return (False, 0)

        if (self.min_value is not None and value < self.min_value) or (
            self.max_value is not None and value > self.max_value
        ):
            raise ValueError(
                f"{value} out of range ({self.min_value} - {self.max_value})"
            )

        return (True, value)

    def encode(self, builder: BinaryPayloadBuilder, value: int):
        assert (self.min_value is None or value >= self.min_value) and (
            self.max_value is None or value <= self.max_value
        )
        builder.add_16bit_uint(value)

    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass(kw_only=True)
class _WordSensorAddress(IdmSensorAddress[int]):
    unit: str | None
    min_value: int | None = None
    max_value: int | None = None

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, int]:
        value = decoder.decode_16bit_int()

        if self.min_value == 0 and value == -1:
            # special case: unavailable
            return (False, 0)

        LOGGER.debug("raw value (int16) for %s: %d", self.name, value)
        if (self.min_value is not None and value < self.min_value) or (
            self.max_value is not None and value > self.max_value
        ):
            raise ValueError(
                f"{value} out of range ({self.min_value} - {self.max_value})"
            )

        return (True, value)

    def encode(self, builder: BinaryPayloadBuilder, value: float):
        assert (self.min_value is None or value >= self.min_value) and (
            self.max_value is None or value <= self.max_value
        )
        builder.add_16bit_uint(value)

    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass(kw_only=True)
class _EnumSensorAddress(IdmSensorAddress[_EnumT], Generic[_EnumT]):
    enum: type[_EnumT]

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, _EnumT]:
        value = decoder.decode_16bit_uint()
        LOGGER.debug("raw value (uint16) for %s: %d", self.name, value)
        if value == 0xFFFF:
            # special case: unavailable
            return (False, self.enum(None))

        try:
            return (True, self.enum(value))
        except ValueError as error:
            raise ValueError(f"decode failed for {value}") from error

    def encode(self, builder: BinaryPayloadBuilder, value: _EnumT):
        builder.add_16bit_uint(value.value)

    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
        )


@dataclass(kw_only=True)
class _BitFieldSensorAddress(IdmSensorAddress[_FlagT], Generic[_FlagT]):
    flag: type[_FlagT]

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> tuple[bool, _FlagT]:
        value = decoder.decode_16bit_uint()
        LOGGER.debug("raw value (uint16) for %s: %d", self.name, value)
        if value == 0xFFFF:
            # special case: unavailable
            return (False, self.flag(None))

        try:
            return (True, self.flag(value))
        except ValueError as error:
            raise ValueError(f"decode failed for {value}") from error

    def encode(self, builder: BinaryPayloadBuilder, value: _FlagT):
        builder.add_16bit_uint(value)

    def entity_description(self, config_entry: ConfigEntry) -> SensorEntityDescription:
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
        )


class HeatingCircuit(Enum):
    """Heating circuit of the IDM heatpump."""

    A = 0
    B = 1
    C = 2
    D = 3
    E = 4
    F = 5
    G = 6


def heating_circuit_sensors(circuit: HeatingCircuit) -> list[IdmSensorAddress]:
    """Get data for heat circuit sensors."""
    offset = circuit.value
    circuit_name = circuit.name.lower()
    return [
        _FloatSensorAddress(
            address=1350 + offset * 2,
            name=f"temp_flow_current_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1364 + offset * 2,
            name=f"temp_room_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1378 + offset * 2,
            name=f"temp_flow_target_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _EnumSensorAddress(
            enum=CircuitMode,
            address=1393 + offset,
            name=f"mode_circuit_{circuit_name}",
        ),
        _FloatSensorAddress(
            address=1401 + offset * 2,
            name=f"temp_room_target_heating_normal_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _FloatSensorAddress(
            address=1415 + offset * 2,
            name=f"temp_room_target_heating_eco_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _FloatSensorAddress(
            address=1429 + offset * 2,
            name=f"curve_circuit_{circuit_name}",
            unit=None,
        ),
        _UCharSensorAddress(
            address=1442 + offset,
            name=f"temp_threshold_heating_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _UCharSensorAddress(
            address=1449 + offset,
            name=f"temp_flow_target_constant_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=5,
            max_value=95,
        ),
        _FloatSensorAddress(
            address=1457 + offset * 2,
            name=f"temp_room_target_cooling_normal_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _FloatSensorAddress(
            address=1471 + offset * 2,
            name=f"temp_room_target_cooling_eco_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _UCharSensorAddress(
            address=1484 + offset,
            name=f"temp_threshold_cooling_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-10,
            max_value=80,
        ),
        _UCharSensorAddress(
            address=1491 + offset,
            name=f"temp_flow_target_cooling_circuit_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=5,
            max_value=95,
        ),
        _EnumSensorAddress(
            enum=ActiveCircuitMode,
            address=1498 + offset,
            name=f"mode_active_circuit_{circuit_name}",
        ),
        _UCharSensorAddress(
            address=1505 + offset,
            name=f"curve_offset_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
        ),
        _FloatSensorAddress(
            address=1650 + offset * 2,
            name=f"temp_external_room_{circuit_name}",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_TEMPERATURE,
        ),
    ]


T = TypeVar("T")

ZONE_OFFSETS = [2000 + 65 * i for i in range(10)]
ROOM_OFFSETS = [2 + 7 * i for i in range(8)]


@dataclass
class ZoneModule:
    """Information about a zone module."""

    index: int
    room_count: int
    room_9_relay: bool

    def __init__(self, index: int, room_count: int, room_9_relay: bool):
        """Initialize zone module."""

        if index < 0 or index > 9:
            raise ValueError("zone index out of range")

        if room_count < 1 or room_count > 8:
            raise ValueError("room count out of range")

        self.index = index
        self.room_count = room_count
        self.room_9_relay = room_9_relay

    def sensors(self) -> list[IdmSensorAddress]:
        """Get data for zone module sensors."""

        return [
            _EnumSensorAddress(
                enum=ZoneMode,
                address=ZONE_OFFSETS[self.index],
                name=f"zone_{self.index+1}_mode",
            ),
            *[
                s
                for room in range(self.room_count)
                for s in [
                    _FloatSensorAddress(
                        address=ZONE_OFFSETS[self.index] + ROOM_OFFSETS[room],
                        name=f"zone_{self.index+1}_room_{room+1}_temp_current",
                        unit=UnitOfTemperature.CELSIUS,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        state_class=SensorStateClass.MEASUREMENT,
                        supported_features=SensorFeatures.SET_TEMPERATURE,
                        min_value=-30,
                        max_value=80,
                    ),
                    _FloatSensorAddress(
                        address=ZONE_OFFSETS[self.index] + ROOM_OFFSETS[room] + 2,
                        name=f"zone_{self.index+1}_room_{room+1}_temp_target",
                        unit=UnitOfTemperature.CELSIUS,
                        device_class=SensorDeviceClass.TEMPERATURE,
                        state_class=SensorStateClass.MEASUREMENT,
                        supported_features=SensorFeatures.SET_TEMPERATURE,
                    ),
                    _UCharSensorAddress(
                        address=ZONE_OFFSETS[self.index] + ROOM_OFFSETS[room] + 4,
                        name=f"zone_{self.index+1}_room_{room+1}_humidity",
                        unit=PERCENTAGE,
                        device_class=SensorDeviceClass.HUMIDITY,
                        state_class=SensorStateClass.MEASUREMENT,
                        supported_features=SensorFeatures.SET_HUMIDITY,
                        min_value=0,
                        max_value=100,
                    ),
                    _EnumSensorAddress(
                        enum=RoomMode,
                        address=ZONE_OFFSETS[self.index] + ROOM_OFFSETS[room] + 5,
                        name=f"zone_{self.index+1}_room_{room+1}_mode",
                        force_single=True,
                        device_class=SensorDeviceClass.ENUM,
                        supported_features=SensorFeatures.SET_ROOM_MODE,
                    ),
                ]
            ],
        ]

    def binary_sensors(self) -> list[IdmBinarySensorAddress]:
        """Get data for zone module binary sensors."""

        sensors = [
            IdmBinarySensorAddress(
                address=ZONE_OFFSETS[self.index] + 1,
                name=f"zone_{self.index+1}_dehumidifier",
            ),
            *[
                IdmBinarySensorAddress(
                    address=ZONE_OFFSETS[self.index] + ROOM_OFFSETS[room] + 6,
                    name=f"zone_{self.index+1}_room_{room+1}_relay",
                )
                for room in range(self.room_count)
            ],
        ]

        if self.room_9_relay:
            sensors.append(
                IdmBinarySensorAddress(
                    address=ZONE_OFFSETS[self.index] + 64,
                    name=f"zone_{self.index+1}_room_9_relay",
                )
            )

        return sensors


SENSOR_ADDRESSES: dict[str, IdmSensorAddress] = {
    s.name: s
    for s in [
        _FloatSensorAddress(
            address=74,
            name="power_solar_surplus",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_POWER,
        ),
        _FloatSensorAddress(
            address=76,
            name="power_resistive_heater",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=78,
            name="power_solar_production",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            supported_features=SensorFeatures.SET_POWER,
        ),
        _FloatSensorAddress(
            address=82,
            name="power_use_house",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            supported_features=SensorFeatures.SET_POWER,
        ),
        _FloatSensorAddress(
            address=84,
            name="power_drain_battery",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_POWER,
        ),
        _WordSensorAddress(
            address=86,
            name="charge_state_battery",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
            supported_features=SensorFeatures.SET_BATTERY,
        ),
        _FloatSensorAddress(
            address=1000,
            name="temp_outside",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1002,
            name="temp_outside_avg",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1004,
            name="failure_id",
            unit=None,
        ),
        _EnumSensorAddress(
            enum=SystemStatus,
            address=1005,
            name="status_system",
            device_class=SensorDeviceClass.ENUM,
            supported_features=SensorFeatures.SET_SYSTEM_STATUS,
        ),
        _EnumSensorAddress(
            enum=SmartGridStatus,
            address=1006,
            name="status_smart_grid",
        ),
        _FloatSensorAddress(
            address=1008,
            name="temp_heat_storage",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1010,
            name="temp_cold_storage",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1012,
            name="temp_water_heater_top",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1014,
            name="temp_water_heater_bottom",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1030,
            name="temp_water_heater_tap",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1032,
            name="temp_water_target",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=5,
            max_value=95,
        ),
        _UCharSensorAddress(
            address=1033,
            name="temp_water_switch_on",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=5,
            max_value=95,
        ),
        _UCharSensorAddress(
            address=1034,
            name="temp_water_switch_off",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=5,
            max_value=95,
        ),
        _FloatSensorAddress(
            address=1048,
            name="price_energy",
            unit=CURRENCY_EURO,
            scale=0.001,
            device_class=SensorDeviceClass.MONETARY,
        ),
        _FloatSensorAddress(
            address=1050,
            name="temp_heat_pump_flow",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1052,
            name="temp_heat_pump_return",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1054,
            name="temp_hgl_flow",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1056,
            name="temp_heat_source_input",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1058,
            name="temp_heat_source_output",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1060,
            name="temp_air_input",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1062,
            name="temp_air_heat_exchanger",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1064,
            name="temp_air_input_2",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _BitFieldSensorAddress(
            flag=HeatPumpStatus,
            address=1090,
            name="status_heat_pump",
        ),
        _WordSensorAddress(
            address=1104,
            name="state_charge_pump",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-1,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1105,
            name="state_brine_pump",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-1,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1106,
            name="state_ground_water_pump",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-1,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1108,
            name="load_isc_cold_storage_pump",
            unit=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1109,
            name="load_isc_recooling_pump",
            unit=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _EnumSensorAddress(
            address=1110,
            name="valve_state_circuit_heating_cooling",
            enum=ValveStateHeatingCooling,
        ),
        _EnumSensorAddress(
            address=1111,
            name="valve_state_storage_heating_cooling",
            enum=ValveStateHeatingCooling,
        ),
        _EnumSensorAddress(
            address=1112,
            name="valve_state_main_heating_water",
            enum=ValveStateHeatingWater,
        ),
        _EnumSensorAddress(
            address=1113,
            name="valve_state_source_heating_cooling",
            enum=ValveStateHeatingCooling,
        ),
        _EnumSensorAddress(
            address=1114,
            name="valve_state_solar_heating_water",
            enum=ValveStateHeatingWater,
        ),
        _EnumSensorAddress(
            address=1115,
            name="valve_state_solar_storage_source",
            enum=ValveStateStorageHeatSource,
        ),
        _EnumSensorAddress(
            address=1116,
            name="valve_state_isc_heating_cooling",
            enum=ValveStateHeatSourceColdStorage,
        ),
        _EnumSensorAddress(
            address=1117,
            name="valve_state_isc_bypass",
            enum=ValveStateStorageBypass,
        ),
        _WordSensorAddress(
            address=1120,
            name="temp_second_source_bivalence_1",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-50,
            max_value=50,
        ),
        _WordSensorAddress(
            address=1121,
            name="temp_second_source_bivalence_2",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-50,
            max_value=50,
        ),
        _WordSensorAddress(
            address=1122,
            name="temp_third_source_bivalence_1",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-50,
            max_value=50,
        ),
        _WordSensorAddress(
            address=1123,
            name="temp_third_source_bivalence_2",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-30,
            max_value=40,
        ),
        _UCharSensorAddress(
            address=1150,
            name="count_running_compressor_stages_heating",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1151,
            name="count_running_compressor_stages_cooling",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1152,
            name="count_running_compressor_stages_water",
            unit=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1392,
            name="humidity",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _FloatSensorAddress(
            address=1690,
            name="temp_external_outdoor",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_TEMPERATURE,
        ),
        _FloatSensorAddress(
            address=1692,
            name="temp_external_humidity",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_HUMIDITY,
            min_value=0,
            max_value=100,
        ),
        _UCharSensorAddress(
            address=1694,
            name="temp_external_request_heating",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_TEMPERATURE,
            min_value=-5,
            max_value=80,
        ),
        _UCharSensorAddress(
            address=1695,
            name="temp_external_request_cooling",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            supported_features=SensorFeatures.SET_TEMPERATURE,
            min_value=-5,
            max_value=80,
        ),
        _FloatSensorAddress(
            address=1750,
            name="energy_heat_total",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1752,
            name="energy_heat_total_cooling",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1754,
            name="energy_heat_total_water",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1756,
            name="energy_heat_total_defrost",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1758,
            name="energy_heat_total_passive_cooling",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1760,
            name="energy_heat_total_solar",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1762,
            name="energy_heat_total_electric",
            unit=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1790,
            name="power_current",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1792,
            name="power_current_solar",
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1850,
            name="temp_solar_collector",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1852,
            name="temp_solar_collector_return",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1854,
            name="temp_solar_charge",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _EnumSensorAddress(
            enum=SolarMode,
            address=1856,
            name="mode_solar",
        ),
        _FloatSensorAddress(
            address=1857,
            name="temp_solar_reference",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1870,
            name="temp_isc_charge_cooling",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1872,
            name="temp_isc_recooling",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _BitFieldSensorAddress(
            flag=IscMode,
            address=1874,
            name="mode_isc",
        ),
        _FloatSensorAddress(
            address=4122,
            name=NAME_POWER_USAGE,
            unit=UnitOfPower.KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
        ),
    ]
}


BINARY_SENSOR_ADDRESSES: dict[str, IdmBinarySensorAddress] = {
    sensor.name: sensor
    for sensor in [
        IdmBinarySensorAddress(
            address=1099,
            name="failure_heat_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        IdmBinarySensorAddress(
            address=1100,
            name="state_compressor_1",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        IdmBinarySensorAddress(
            address=1101,
            name="state_compressor_2",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        IdmBinarySensorAddress(
            address=1102,
            name="state_compressor_3",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        IdmBinarySensorAddress(
            address=1103,
            name="state_compressor_4",
            device_class=BinarySensorDeviceClass.RUNNING,
        ),
        IdmBinarySensorAddress(
            address=1710,
            name="request_heating",
            supported_features=SensorFeatures.SET_BINARY,
        ),
        IdmBinarySensorAddress(
            address=1711,
            name="request_cooling",
            supported_features=SensorFeatures.SET_BINARY,
        ),
        IdmBinarySensorAddress(
            address=1712,
            name="request_water",
            supported_features=SensorFeatures.SET_BINARY,
        ),
    ]
}


SENSOR_NAMES: dict[int, str] = {
    74: "Aktueller PV-Überschuss",
    76: "Leistung E-Heizstab",
    78: "Aktuelle PV Produktion",
    82: "Hausverbrauch",
    84: "Batterieentladung",
    86: "Batterie Füllstand",
    1000: "Außentemperatur",
    1002: "Gemittelte Außentemperatur",
    1004: "Aktuelle Störungsnummer",
    1005: "Betriebsart System",
    1006: "Smart Grid Status",
    1008: "Wärmespeichertemperatur",
    1010: "Kältespeichertemperatur",
    1012: "Trinkwassererwärmertemperatur unten",
    1014: "Trinkwassererwärmertemperatur oben",
    1030: "Warmwasserzapftemperatur",
    1032: "Warmwasser-Solltemperatur",
    1033: "Warmwasserladung Einschalttemperatur",
    1034: "Warmwasserladung Ausschalttemperatur",
    1048: "Aktueller Strompreis",
    1050: "Wärmepumpen Vorlauftemperatur",
    1052: "Wärmepumpen Rücklauftemperatur",
    1054: "HGL Vorlauftemperatur",
    1056: "Wärmequelleneintrittstemperatur",
    1058: "Wärmequellenaustrittstemperatur",
    1060: "Luftansaugtemperatur",
    1062: "Luftwärmetauschertemperatur",
    1064: "Luftansaugtemperatur 2",
    1090: "Betriebsart Wärmepumpe",
    1091: "Heizanforderung",  # TODO
    1092: "Kühlanforderung",  # TODO
    1093: "Vorranganforderung",  # TODO
    1098: "EW/WVU Sperrkontakt",  # TODO
    1099: "Summenstörung Wärmepumpe",
    1100: "Status Verdichter 1",
    1101: "Status Verdichter 2",
    1102: "Status Verdichter 3",
    1103: "Status Verdichter 4",
    1104: "Status Ladepumpe",
    1105: "Status Sole/Zwischenkreispumpe",
    1106: "Status Wärmequellen/Grundwasserpumpe",
    1108: "Status ISC Kältespeicherpumpe",
    1109: "Status ISC Rückkühlpumpe",
    1110: "Umschaltventil Heizkreis Heizen/Kühlen",
    1111: "Umschaltventil Speicher Heizen/Kühlen",
    1112: "Umschaltventil Heizen/Warmwasser",
    1113: "Umschaltventil Wärmequelle Heizen/Kühlen",
    1114: "Umschaltventil Solar Heizen/Warmwasser",
    1115: "Umschaltventil Solar Speicher/Wärmequelle",
    1116: "Umschaltventil ISC Wärmequelle/Kältespeicher",
    1117: "Umschaltventil ISC Speicher/Bypass",
    1118: "Zirkulationspumpe",  # TODO
    1120: "2. Wärmeerzeuger - Bivalenzpunkt 1",
    1121: "2. Wärmeerzeuger - Bivalenzpunkt 2",
    1122: "3. Wärmeerzeuger - Bivalenzpunkt 1",
    1123: "3. Wärmeerzeuger - Bivalenzpunkt 2",
    1124: "2./3. Wärmeerzeuger",  # TODO
    1150: "Anzahl laufende Verdichterstufen Heizen",
    1151: "Anzahl laufende Verdichterstufen Kühlen",
    1152: "Anzahl laufende Verdichterstufen Warmwasser",
    1350: "Heizkreis A Vorlauftemperatur",
    1352: "Heizkreis B Vorlauftemperatur",
    1354: "Heizkreis C Vorlauftemperatur",
    1356: "Heizkreis D Vorlauftemperatur",
    1358: "Heizkreis E Vorlauftemperatur",
    1360: "Heizkreis F Vorlauftemperatur",
    1362: "Heizkreis G Vorlauftemperatur",
    1364: "Heizkreis A Raumtemperatur",
    1366: "Heizkreis B Raumtemperatur",
    1368: "Heizkreis C Raumtemperatur",
    1370: "Heizkreis D Raumtemperatur",
    1372: "Heizkreis E Raumtemperatur",
    1374: "Heizkreis F Raumtemperatur",
    1376: "Heizkreis G Raumtemperatur",
    1378: "Heizkreis A Sollvorlauftemperatur",
    1380: "Heizkreis B Sollvorlauftemperatur",
    1382: "Heizkreis C Sollvorlauftemperatur",
    1384: "Heizkreis D Sollvorlauftemperatur",
    1386: "Heizkreis E Sollvorlauftemperatur",
    1388: "Heizkreis F Sollvorlauftemperatur",
    1390: "Heizkreis G Sollvorlauftemperatur",
    1392: "Feuchtesensor",
    1393: "Betriebsart Heizkreis A",
    1394: "Betriebsart Heizkreis B",
    1395: "Betriebsart Heizkreis C",
    1396: "Betriebsart Heizkreis D",
    1397: "Betriebsart Heizkreis E",
    1398: "Betriebsart Heizkreis F",
    1399: "Betriebsart Heizkreis G",
    1401: "Raumsolltemperatur Heizen Normal HK A",
    1403: "Raumsolltemperatur Heizen Normal HK B",
    1405: "Raumsolltemperatur Heizen Normal HK C",
    1407: "Raumsolltemperatur Heizen Normal HK D",
    1409: "Raumsolltemperatur Heizen Normal HK E",
    1411: "Raumsolltemperatur Heizen Normal HK F",
    1413: "Raumsolltemperatur Heizen Normal HK G",
    1415: "Raumsolltemperatur Heizen Eco HK A",
    1417: "Raumsolltemperatur Heizen Eco HK B",
    1419: "Raumsolltemperatur Heizen Eco HK C",
    1421: "Raumsolltemperatur Heizen Eco HK D",
    1423: "Raumsolltemperatur Heizen Eco HK E",
    1425: "Raumsolltemperatur Heizen Eco HK F",
    1427: "Raumsolltemperatur Heizen Eco HK G",
    1429: "Heizkurve HK A",
    1431: "Heizkurve HK B",
    1433: "Heizkurve HK C",
    1435: "Heizkurve HK D",
    1437: "Heizkurve HK E",
    1439: "Heizkurve HK F",
    1441: "Heizkurve HK G",
    1442: "Heizgrenze HK A",
    1443: "Heizgrenze HK B",
    1444: "Heizgrenze HK C",
    1445: "Heizgrenze HK D",
    1446: "Heizgrenze HK E",
    1447: "Heizgrenze HK F",
    1448: "Heizgrenze HK G",
    1449: "Sollvorlauftemperatur HK A (Konstant-HK)",
    1450: "Sollvorlauftemperatur HK B (Konstant-HK)",
    1451: "Sollvorlauftemperatur HK C (Konstant-HK)",
    1452: "Sollvorlauftemperatur HK D (Konstant-HK)",
    1453: "Sollvorlauftemperatur HK E (Konstant-HK)",
    1454: "Sollvorlauftemperatur HK F (Konstant-HK)",
    1455: "Sollvorlauftemperatur HK G (Konstant-HK)",
    1457: "Raumsolltemperatur Kühlen Normal HK A",
    1459: "Raumsolltemperatur Kühlen Normal HK B",
    1461: "Raumsolltemperatur Kühlen Normal HK C",
    1463: "Raumsolltemperatur Kühlen Normal HK D",
    1465: "Raumsolltemperatur Kühlen Normal HK E",
    1467: "Raumsolltemperatur Kühlen Normal HK F",
    1469: "Raumsolltemperatur Kühlen Normal HK G",
    1471: "Raumsolltemperatur Kühlen Eco HK A",
    1473: "Raumsolltemperatur Kühlen Eco HK B",
    1475: "Raumsolltemperatur Kühlen Eco HK C",
    1477: "Raumsolltemperatur Kühlen Eco HK D",
    1479: "Raumsolltemperatur Kühlen Eco HK E",
    1481: "Raumsolltemperatur Kühlen Eco HK F",
    1483: "Raumsolltemperatur Kühlen Eco HK G",
    1484: "Kühlgrenze HK A",
    1485: "Kühlgrenze HK B",
    1486: "Kühlgrenze HK C",
    1487: "Kühlgrenze HK D",
    1488: "Kühlgrenze HK E",
    1489: "Kühlgrenze HK F",
    1490: "Kühlgrenze HK G",
    1491: "Sollvorlauftemperatur Kühlen HK A",
    1492: "Sollvorlauftemperatur Kühlen HK B",
    1493: "Sollvorlauftemperatur Kühlen HK C",
    1494: "Sollvorlauftemperatur Kühlen HK D",
    1495: "Sollvorlauftemperatur Kühlen HK E",
    1496: "Sollvorlauftemperatur Kühlen HK F",
    1497: "Sollvorlauftemperatur Kühlen HK G",
    1498: "Aktive Betriebsart Heizkreis A",
    1499: "Aktive Betriebsart Heizkreis B",
    1500: "Aktive Betriebsart Heizkreis C",
    1501: "Aktive Betriebsart Heizkreis D",
    1502: "Aktive Betriebsart Heizkreis E",
    1503: "Aktive Betriebsart Heizkreis F",
    1504: "Aktive Betriebsart Heizkreis G",
    1505: "Parallelverschiebung HK A",
    1506: "Parallelverschiebung HK B",
    1507: "Parallelverschiebung HK C",
    1508: "Parallelverschiebung HK D",
    1509: "Parallelverschiebung HK E",
    1510: "Parallelverschiebung HK F",
    1511: "Parallelverschiebung HK G",
    1650: "Externe Raumtemperatur HK A",
    1652: "Externe Raumtemperatur HK B",
    1654: "Externe Raumtemperatur HK C",
    1656: "Externe Raumtemperatur HK D",
    1658: "Externe Raumtemperatur HK E",
    1660: "Externe Raumtemperatur HK F",
    1662: "Externe Raumtemperatur HK G",
    1690: "Externe Außentemperatur",
    1692: "Externe Feuchte",
    1694: "Externe Anforderungstemperatur Heizen",
    1695: "Externe Anforderungstemperatur Kühlen",
    1696: "GLT Temperaturanforderung Heizen",
    1698: "GLT Temperaturanfoderung Kühlen",
    1710: "Anforderung Heizen",
    1711: "Anforderung Kühlen",
    1712: "Anforderung Warmwasserladung",
    1713: "Externe Ansteuerung einmalige Warmwasserladung",  # TODO
    1714: "Externe Anforderung Sole-/Zwischenkreispumpe",  # TODO
    1715: "Externe Anforderung Grundwasserpumpe",  # TODO
    1716: "GLT Wärmespeichertemperatur",
    1718: "GLT Kältespeichertemperatur",
    1720: "GLT TWW-Erwärmertemperatur unten",
    1722: "GLT TWW-Erwärmertemperatur oben",
    1748: "Wärmemenge Heizen",
    1750: "Wärmemenge Heizen",
    1752: "Wärmemenge Kühlen",
    1754: "Wärmemenge Warmwasser",
    1756: "Wärmemenge Abtauung",
    1758: "Wärmemenge Passive Kühlung",
    1760: "Wärmemenge Solar",
    1762: "Wärmemenge Elektroheizeinsatz",
    1790: "Momentanleistung",
    1792: "Momentanleistung Solar",
    1850: "Solar Kollektortemperatur",
    1852: "Solar Kollektorrücklauftemperatur",
    1854: "Solar Ladetemperatur",
    1856: "Betriebsart Solar",
    1857: "Solar WQ-Referenztemperatur/Pooltemperatur",
    1870: "ISC Ladetemperatur Kühlen",
    1872: "ISC Rückkühltemperatur",
    1874: "ISC Modus",
    1999: "Störmeldungen quittieren",
    4108: "Leistungsbegrenzung Wärmepumpe",  # TODO
    4112: "Leistungsbegrenzung Kaskade",  # TODO
    4116: "Firmware Version IDM",  # TODO
    4122: "Aktuelle Leistungsaufnahme Wärmepumpe",
    4124: "elektrische Gesamtleistung",  # TODO
    4126: "thermische Leistung (basierend auf Durchflusssensor)",  # TODO
    4128: "Wärmemenge gesamt",  # TODO
    **dict(
        zn
        for zone in range(10)
        for zn in [
            (ZONE_OFFSETS[zone], f"Zonenmodul {zone+1} Modus"),
            (ZONE_OFFSETS[zone] + 1, f"Zonenmodul {zone+1} Entfeuchtungsausgang"),
            *[
                rn
                for room in range(8)
                for rn in [
                    (
                        ZONE_OFFSETS[zone] + ROOM_OFFSETS[room],
                        f"Zonenmodul {zone+1} Raum {room+1} Raumtemperatur",
                    ),
                    (
                        ZONE_OFFSETS[zone] + ROOM_OFFSETS[room] + 2,
                        f"Zonenmodul {zone+1} Raum {room+1} Raumsolltemperatur",
                    ),
                    (
                        ZONE_OFFSETS[zone] + ROOM_OFFSETS[room] + 4,
                        f"Zonenmodul {zone+1} Raum {room+1} Raumfeuchte",
                    ),
                    (
                        ZONE_OFFSETS[zone] + ROOM_OFFSETS[room] + 5,
                        f"Zonenmodul {zone+1} Raum {room+1} Betriebsart",
                    ),
                    (
                        ZONE_OFFSETS[zone] + ROOM_OFFSETS[room] + 6,
                        f"Zonenmodul {zone+1} Raum {room+1} Status Relais",
                    ),
                ]
            ],
            (ZONE_OFFSETS[zone] + 64, f"Zonenmodul {zone+1} Raum 9 Status Relais"),
        ]
    ),
}
