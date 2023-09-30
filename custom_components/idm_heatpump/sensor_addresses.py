"""Sensor addresses."""

from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.const import (
    CURRENCY_EURO,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE,
    POWER_KILO_WATT,
    TEMP_CELSIUS,
)
from pymodbus.payload import BinaryPayloadDecoder

from .const import CONF_DISPLAY_NAME


@dataclass
class IdmSensorAddress(ABC):
    """Describes one of the sensors of an IDM heatpump."""

    address: int
    name: str
    device_class: SensorDeviceClass
    state_class: SensorStateClass

    @abstractproperty
    def size(self) -> int:
        """Get number of registers this sensor's value occupies."""

    @abstractmethod
    def decode(self, decoder: BinaryPayloadDecoder):
        """Decode this sensor's value."""

    def entity_description(self, config_entry) -> SensorEntityDescription:
        """Get SensorEntityDescription for this sensor."""


@dataclass
class IdmBinarySensorAddress:
    """Describes one of the binary sensors of an IDM heatpump."""

    address: int
    name: str
    device_class: BinarySensorDeviceClass

    @property
    def size(self) -> int:
        """Number of registers this sensor's value occupies."""
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> bool:
        """Decode this sensor's value."""
        value = decoder.decode_16bit_uint()
        return value == 1

    def entity_description(self, config_entry) -> BinarySensorEntityDescription:
        """SensorEntityDescription for this sensor."""
        return BinarySensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
        )


@dataclass
class _FloatSensorAddress(IdmSensorAddress):
    unit: str
    decimal_digits: int = 2
    scale: float = 1
    min_value: float | None = None
    max_value: float | None = 0xFFFE

    @property
    def size(self):
        return 2

    def decode(self, decoder: BinaryPayloadDecoder) -> float:
        value = round(decoder.decode_32bit_float() * self.scale, self.decimal_digits)
        return (
            None
            if (self.min_value is not None and value < self.min_value)
            or (self.max_value is not None and value > self.max_value)
            else value
        )

    def entity_description(self, config_entry):
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass
class _UCharSensorAddress(IdmSensorAddress):
    unit: str
    min_value: int | None = None
    max_value: int | None = 0xFFFE

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> int:
        value = decoder.decode_16bit_uint()
        return (
            None
            if (self.min_value is not None and value < self.min_value)
            or (self.max_value is not None and value > self.max_value)
            else value
        )

    def entity_description(self, config_entry):
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass
class _WordSensorAddress(IdmSensorAddress):
    unit: str
    min_value: int | None = None
    max_value: int | None = None

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> int:
        value = decoder.decode_16bit_uint()
        return (
            None
            if (self.min_value is not None and value < self.min_value)
            or (self.max_value is not None and value > self.max_value)
            else value
        )

    def entity_description(self, config_entry):
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
            native_unit_of_measurement=self.unit,
        )


@dataclass
class _EnumSensorAddress(IdmSensorAddress):
    value_labels: dict[int, str]

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> str:
        value = decoder.decode_16bit_uint()
        if value == 0xFFFF:
            return None
        return self.value_labels.get(value)

    def entity_description(self, config_entry):
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
        )


@dataclass
class _BitFieldSensorAddress(IdmSensorAddress):
    bit_labels: dict[int, str]

    @property
    def size(self):
        return 1

    def decode(self, decoder: BinaryPayloadDecoder) -> str:
        value = decoder.decode_16bit_uint()
        if value == 0xFFFF:
            return None
        if value == 0:
            return self.bit_labels.get(0)

        return ", ".join(
            [label for bit, label in self.bit_labels.items() if value & bit != 0]
        )

    def entity_description(self, config_entry):
        return SensorEntityDescription(
            key=self.name,
            name=f"{config_entry.data.get(CONF_DISPLAY_NAME)}: {SENSOR_NAMES.get(self.address)}",
            device_class=self.device_class,
            state_class=self.state_class,
        )


def heat_circuit_sensors(circuit) -> list[IdmSensorAddress]:
    """Get data for heat circuit sensors."""
    offset = ord(circuit) - ord("a")
    return [
        _FloatSensorAddress(
            address=1350 + offset * 2,
            name=f"temp_flow_current_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _FloatSensorAddress(
            address=1364 + offset * 2,
            name=f"temp_room_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _FloatSensorAddress(
            address=1378 + offset * 2,
            name=f"temp_flow_target_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _EnumSensorAddress(
            address=1393 + offset,
            name=f"mode_circuit_{circuit}",
            value_labels={
                0: "off",
                1: "timed",
                2: "normal",
                3: "eco",
                4: "manual_heat",
                5: "manual_cool",
            },
            device_class=None,
            state_class=None,
        ),
        _FloatSensorAddress(
            address=1401 + offset * 2,
            name=f"temp_room_target_heating_normal_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=15,
            max_value=30,
        ),
        _FloatSensorAddress(
            address=1415 + offset * 2,
            name=f"temp_room_target_heating_eco_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=10,
            max_value=25,
        ),
        _FloatSensorAddress(
            address=1429 + offset * 2,
            name=f"curve_circuit_{circuit}",
            unit=None,
            device_class=None,
            state_class=None,
            min_value=0.1,
            max_value=3.5,
        ),
        _UCharSensorAddress(
            address=1442 + offset,
            name=f"temp_threshold_heating_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=50,
        ),
        _UCharSensorAddress(
            address=1449 + offset,
            name=f"temp_flow_target_constant_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=20,
            max_value=90,
        ),
        _FloatSensorAddress(
            address=1457 + offset * 2,
            name=f"temp_room_target_cooling_normal_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=15,
            max_value=30,
        ),
        _FloatSensorAddress(
            address=1471 + offset * 2,
            name=f"temp_room_target_cooling_eco_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=15,
            max_value=30,
        ),
        _UCharSensorAddress(
            address=1484 + offset,
            name=f"temp_threshold_cooling_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=36,
        ),
        _UCharSensorAddress(
            address=1491 + offset,
            name=f"temp_flow_target_cooling_circuit_{circuit}",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=8,
            max_value=30,
        ),
        _EnumSensorAddress(
            address=1498 + offset,
            name=f"mode_active_circuit_{circuit}",
            value_labels={
                0: "off",
                1: "heating",
                2: "cooling",
            },
            device_class=None,
            state_class=None,
        ),
        _UCharSensorAddress(
            address=1505 + offset,
            name=f"curve_offset_{circuit}",
            unit=PERCENTAGE,
            device_class=None,
            state_class=None,
            min_value=0,
            max_value=30,
        ),
    ]


SENSOR_ADDRESSES: dict[str, IdmSensorAddress] = {
    s.name: s
    for s in [
        _FloatSensorAddress(
            address=1000,
            name="temp_outside",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1002,
            name="temp_outside_avg",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1004,
            name="failure_id",
            unit="",
            device_class=None,
            state_class=None,
        ),
        _EnumSensorAddress(
            address=1005,
            name="status_system",
            value_labels={
                0: "standby",
                1: "automatic",
                2: "away",
                4: "hot_water_only",
                5: "heating_cooling_only",
            },
            device_class=None,
            state_class=None,
        ),
        _EnumSensorAddress(
            address=1006,
            name="status_smart_grid",
            value_labels={
                0: "grid_blocked_solar_off",
                1: "grid_allowed_solar_off",
                2: "grid_unused_solar_on",
                4: "grid_blocked_solar_on",
            },
            device_class=None,
            state_class=None,
        ),
        _FloatSensorAddress(
            address=1008,
            name="temp_heat_storage",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1010,
            name="temp_cold_storage",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1012,
            name="temp_water_heater_top",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1014,
            name="temp_water_heater_bottom",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1030,
            name="temp_water_heater_tap",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1032,
            name="temp_water_target",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=35,
            max_value=95,
        ),
        _UCharSensorAddress(
            address=1033,
            name="temp_water_switch_on",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=30,
            max_value=50,
        ),
        _UCharSensorAddress(
            address=1034,
            name="temp_water_switch_off",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=46,
            max_value=53,
        ),
        _FloatSensorAddress(
            address=1048,
            name="price_energy",
            unit=CURRENCY_EURO,
            scale=0.001,
            device_class=SensorDeviceClass.MONETARY,
            state_class=None,
        ),
        _FloatSensorAddress(
            address=1050,
            name="temp_heat_pump_flow",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1052,
            name="temp_heat_pump_return",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1054,
            name="temp_hgl_flow",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1056,
            name="temp_heat_source_input",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1058,
            name="temp_heat_source_output",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1060,
            name="temp_air_input",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1062,
            name="temp_air_heat_exchanger",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1064,
            name="temp_air_input_2",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _BitFieldSensorAddress(
            address=1090,
            name="status_heat_pump",
            bit_labels={
                0: "off",
                1: "heating",
                2: "cooling",
                4: "water",
                8: "defrosting",
            },
            device_class=None,
            state_class=None,
        ),
        _WordSensorAddress(
            address=1104,
            name="load_charge_pump",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1105,
            name="load_brine_pump",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1106,
            name="load_ground_water_pump",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1108,
            name="load_isc_cold_storage_pump",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1109,
            name="load_isc_recooling_pump",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1110,
            name="valve_state_circuit_heating_cooling",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1111,
            name="valve_state_storage_heating_cooling",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1112,
            name="valve_state_main_heating_water",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1113,
            name="valve_state_source_heating_cooling",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1114,
            name="valve_state_solar_heating_water",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1115,
            name="valve_state_solar_storage_source",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1116,
            name="valve_state_isc_heating_cooling",
            unit=PERCENTAGE,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _WordSensorAddress(
            address=1120,
            name="temp_second_source_bivalence_1",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-30,
            max_value=40,
        ),
        _WordSensorAddress(
            address=1121,
            name="temp_second_source_bivalence_2",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-30,
            max_value=40,
        ),
        _WordSensorAddress(
            address=1122,
            name="temp_third_source_bivalence_1",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-30,
            max_value=40,
        ),
        _WordSensorAddress(
            address=1123,
            name="temp_third_source_bivalence_2",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=-30,
            max_value=40,
        ),
        _UCharSensorAddress(
            address=1150,
            name="count_running_compressor_stages_heating",
            unit=None,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1151,
            name="count_running_compressor_stages_cooling",
            unit=None,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _UCharSensorAddress(
            address=1152,
            name="count_running_compressor_stages_water",
            unit=None,
            device_class=None,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        *heat_circuit_sensors("a"),
        *heat_circuit_sensors("b"),
        *heat_circuit_sensors("c"),
        *heat_circuit_sensors("d"),
        *heat_circuit_sensors("e"),
        *heat_circuit_sensors("f"),
        *heat_circuit_sensors("g"),
        _FloatSensorAddress(
            address=1392,
            name="humidity",
            unit=PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
            max_value=100,
        ),
        _UCharSensorAddress(
            address=1694,
            name="temp_external_request_heating",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=20,
            max_value=65,
        ),
        _UCharSensorAddress(
            address=1695,
            name="temp_external_request_cooling",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=10,
            max_value=25,
        ),
        _FloatSensorAddress(
            address=1750,
            name="energy_heat_total",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1752,
            name="energy_heat_total_cooling",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1754,
            name="energy_heat_total_water",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1756,
            name="energy_heat_total_defrost",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1758,
            name="energy_heat_total_passive_cooling",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1760,
            name="energy_heat_total_solar",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1762,
            name="energy_heat_total_electric",
            unit=ENERGY_KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1790,
            name="power_current",
            unit=POWER_KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1792,
            name="power_current_solar",
            unit=POWER_KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=1850,
            name="temp_solar_collector",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1852,
            name="temp_solar_collector_return",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1854,
            name="temp_solar_charge",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _EnumSensorAddress(
            address=1856,
            name="mode_solar",
            value_labels={
                0: "auto",
                1: "water",
                2: "heating",
                3: "water_heating",
                4: "source_pool",
            },
            device_class=None,
            state_class=None,
        ),
        _FloatSensorAddress(
            address=1857,
            name="temp_solar_reference",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1870,
            name="temp_isc_charge_cooling",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _FloatSensorAddress(
            address=1872,
            name="temp_isc_recooling",
            unit=TEMP_CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        _BitFieldSensorAddress(
            address=1874,
            name="mode_isc",
            bit_labels={
                0: "none",
                1: "heating",
                4: "water",
                8: "source",
            },
            device_class=None,
            state_class=None,
        ),
        _FloatSensorAddress(
            address=74,
            name="power_solar_surplus",
            unit=POWER_KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=78,
            name="power_solar_production",
            unit=POWER_KILO_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            min_value=0,
        ),
        _FloatSensorAddress(
            address=4122,
            name="power_current_draw",
            unit=POWER_KILO_WATT,
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
            name="failure_compressor_1",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        IdmBinarySensorAddress(
            address=1101,
            name="failure_compressor_2",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        IdmBinarySensorAddress(
            address=1102,
            name="failure_compressor_3",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        IdmBinarySensorAddress(
            address=1103,
            name="failure_compressor_4",
            device_class=BinarySensorDeviceClass.PROBLEM,
        ),
        IdmBinarySensorAddress(
            address=1710,
            name="request_heating",
            device_class=None,
        ),
        IdmBinarySensorAddress(
            address=1711,
            name="request_cooling",
            device_class=None,
        ),
        IdmBinarySensorAddress(
            address=1712,
            name="request_water",
            device_class=None,
        ),
    ]
}

SENSOR_NAMES: dict[int, str] = {
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
    1120: "2. Wärmeerzeuger - Bivalenzpunkt 1",
    1121: "2. Wärmeerzeuger - Bivalenzpunkt 2",
    1122: "3. Wärmeerzeuger - Bivalenzpunkt 1",
    1123: "3. Wärmeerzeuger - Bivalenzpunkt 2",
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
    1710: "Anforderung Heizen",
    1711: "Anforderung Kühlen",
    1712: "Anforderung Warmwasserladung",
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
    74: "Aktueller PV-Überschuss",
    78: "Aktueller PV Produktion",
    4122: "Aktuelle Leistungsaufnahme Wärmepumpe",
}
