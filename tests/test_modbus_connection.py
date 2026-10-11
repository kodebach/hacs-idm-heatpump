"""Tests for the Modbus connection migration."""

import sys
from pathlib import Path
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase

from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

# Import the unit under test without executing integration setup, which depends
# on shared-unit APIs that are newer than the PyPI Home Assistant package.
integration_package = ModuleType("custom_components.idm_heatpump")
integration_package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "idm_heatpump")
]
sys.modules.setdefault("custom_components.idm_heatpump", integration_package)

from custom_components.idm_heatpump.const import CircuitMode, HeatPumpStatus  # noqa: E402
from custom_components.idm_heatpump.idm_heatpump import (  # noqa: E402
    IdmHeatpump,
    _FetchError,
)
from custom_components.idm_heatpump.sensor_addresses import (  # noqa: E402
    _BitFieldSensorAddress,
    _EnumSensorAddress,
    _FloatSensorAddress,
    _UCharSensorAddress,
    _WordSensorAddress,
    IdmBinarySensorAddress,
)


class SensorAddressCodecTests(TestCase):
    """Verify the raw value formats used by the heat pump."""

    def test_float32_uses_little_word_order(self):
        """Preserve the IDM low-word-first float encoding."""
        address = _FloatSensorAddress(address=10, name="float", unit=None)

        self.assertTrue(address.is_float)
        self.assertEqual(address.size, 2)
        self.assertEqual(address.decode([0x0000, 0x4148]), (True, 12.5))
        self.assertEqual(address.encode(12.5), [0x0000, 0x4148])

    def test_signed_unsigned_and_enum_values(self):
        """Round-trip signed, unsigned, and enum register formats."""
        signed = _WordSensorAddress(address=10, name="signed", unit=None)
        unsigned = _UCharSensorAddress(address=11, name="unsigned", unit=None)
        enum = _EnumSensorAddress(
            address=12,
            name="mode",
            enum=CircuitMode,
        )

        self.assertFalse(signed.is_float)
        self.assertEqual(signed.size, 1)
        self.assertEqual(signed.decode([0xFF85]), (True, -123))
        self.assertEqual(signed.encode(-123), [0xFF85])
        self.assertEqual(unsigned.decode([0xBEEF]), (True, 0xBEEF))
        self.assertEqual(unsigned.encode(0xBEEF), [0xBEEF])
        self.assertEqual(enum.decode([3]), (True, CircuitMode.ECO))
        self.assertEqual(enum.encode(CircuitMode.ECO), [3])

    def test_flag_values_and_sentinel(self):
        """Decode defined flag values and the unavailable sentinel."""
        address = _BitFieldSensorAddress(
            address=10,
            name="status",
            flag=HeatPumpStatus,
        )

        self.assertEqual(address.decode([1]), (True, HeatPumpStatus.HEATING))
        self.assertEqual(address.encode(HeatPumpStatus.HEATING), [1])
        self.assertEqual(address.decode([0xFFFF]), (False, HeatPumpStatus.OFF))

    def test_binary_sensor_values(self):
        """Decode and encode binary sensor register values."""
        address = IdmBinarySensorAddress(address=10, name="binary")

        self.assertEqual(address.decode([0]), (True, False))
        self.assertEqual(address.decode([1]), (True, True))
        self.assertEqual(address.encode(False), [0])
        self.assertEqual(address.encode(True), [1])


class IdmHeatpumpModbusTests(IsolatedAsyncioTestCase):
    """Exercise the ModbusUnit boundary without connecting to a device."""

    async def asyncSetUp(self) -> None:
        """Create a heat pump backed by a mock unit."""
        self.connection = MockModbusConnection()
        self.unit: MockModbusUnit = self.connection.for_unit(1)
        self.unit.input.update({10: 0x0000, 11: 0x4148})
        self.heatpump = IdmHeatpump(
            unit=self.unit,
            circuits=[],
            zones=[],
            no_groups=True,
            max_power_usage=None,
        )
        self.address = _FloatSensorAddress(address=10, name="float", unit=None)
        self.group = IdmHeatpump._SensorGroup(
            start=self.address.address,
            count=self.address.size,
            sensors=[self.address],
        )

    async def test_group_read_retries_and_decodes(self):
        """Recover after a transient error and decode the retry response."""
        failed_once = True

        def read_register():
            nonlocal failed_once
            if failed_once:
                failed_once = False
                raise ModbusConnectionError("temporary connection failure")
            return 0

        self.unit.input[10] = read_register

        data = await self.heatpump._fetch_sensors(self.group)

        self.assertEqual(data, {"float": 12.5})
        self.assertEqual(
            [(event.address, event.count) for event in self.unit.read_events],
            [(10, 2), (10, 2)],
        )

    async def test_group_read_retries_connection_errors(self):
        """Retry a persistent connection error once before failing."""
        self.unit.fail_read(
            10,
            ModbusConnectionError("temporary connection failure"),
            register_type="input",
        )

        with self.assertRaises(_FetchError):
            await self.heatpump._fetch_sensors(self.group)

        self.assertEqual(
            [(event.address, event.count) for event in self.unit.read_events],
            [(10, 2), (10, 2)],
        )

    async def test_binary_sensor_group_read(self):
        """Read and decode a binary sensor through the Modbus unit."""
        self.unit.input[20] = 1
        address = IdmBinarySensorAddress(address=20, name="binary")
        group = IdmHeatpump._SensorGroup(
            start=address.address,
            count=address.size,
            sensors=[address],
        )

        self.assertEqual(await self.heatpump._fetch_sensors(group), {"binary": True})

    async def test_write_uses_multiple_register_operation(self):
        """Write encoded words through ModbusUnit's FC16 operation."""
        writes = []
        self.unit.on_write(writes.append)

        await self.heatpump.async_write_value(self.address, 12.5)

        self.assertEqual(self.unit.holding, {10: 0x0000, 11: 0x4148})
        self.assertEqual(writes[0].register_type, "holding")
        self.assertEqual(writes[0].address, 10)
        self.assertEqual(writes[0].values, [0x0000, 0x4148])
        self.assertEqual(writes[0].function_code, 0x10)
