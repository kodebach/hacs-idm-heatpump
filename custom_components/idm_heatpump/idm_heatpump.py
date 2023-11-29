"""Abstraction over the modbus interface of IDM heatpumps."""

import asyncio
from dataclasses import dataclass
import collections
from typing import TypeVar

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ModbusResponse
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.register_read_message import ReadInputRegistersResponse

from .const import NAME_POWER_USAGE
from .logger import LOGGER
from .sensor_addresses import (
    BINARY_SENSOR_ADDRESSES,
    SENSOR_ADDRESSES,
    HeatingCircuit,
    BaseSensorAddress,
    ZoneModule,
    heating_circuit_sensors,
)

_T = TypeVar("_T")


class IdmHeatpump:
    """Abstraction over the modbus interface of IDM heatpumps."""

    @dataclass
    class _SensorGroup:
        start: int
        count: int
        sensors: list[BaseSensorAddress]

    client: AsyncModbusTcpClient
    sensors: list[BaseSensorAddress]
    sensor_groups: list[_SensorGroup] = []
    max_power_usage: float | None

    def __init__(
        self,
        hostname: str,
        circuits: list[HeatingCircuit],
        zones: list[ZoneModule],
        no_groups: bool,
        max_power_usage: float | None,
    ) -> None:
        """Create heatpump."""
        self.client = AsyncModbusTcpClient(host=hostname)

        self.max_power_usage = max_power_usage

        self.sensors = sorted(
            [
                *SENSOR_ADDRESSES.values(),
                *BINARY_SENSOR_ADDRESSES.values(),
                *[s for c in circuits for s in heating_circuit_sensors(c)],
                *[s for zone in zones for s in zone.sensors()],
                *[s for zone in zones for s in zone.binary_sensors()],
            ],
            key=lambda s: s.address,
        )
        addresses = sorted([s.address for s in self.sensors])
        duplicate_addresses = [
            [s for s in self.sensors if s.address == address]
            for address, count in collections.Counter(addresses).items()
            if count > 1
        ]
        if len(duplicate_addresses) > 0:
            raise Exception(  # pylint: disable=broad-exception-raised
                f"duplicate address(es) detected: {duplicate_addresses}"
            )

        if no_groups:
            self.sensor_groups = [
                IdmHeatpump._SensorGroup(
                    start=sensor.address,
                    count=sensor.size,
                    sensors=[sensor],
                )
                for sensor in self.sensors
            ]
        else:
            for sensor in self.sensors:
                last_address = (
                    None
                    if len(self.sensor_groups) == 0
                    else self.sensor_groups[-1].start + self.sensor_groups[-1].count
                )

                if (
                    # first group
                    len(self.sensor_groups) == 0
                    # group sensors to at most 32 registers
                    or self.sensor_groups[-1].count + sensor.size > 32
                    # start new group when forced
                    or sensor.force_single
                    or self.sensor_groups[-1].sensors[-1].force_single
                    # not contiouus need new group
                    or sensor.address != last_address
                ):
                    self.sensor_groups.append(
                        IdmHeatpump._SensorGroup(
                            start=sensor.address,
                            count=sensor.size,
                            sensors=[sensor],
                        )
                    )
                else:
                    self.sensor_groups[-1] = IdmHeatpump._SensorGroup(
                        start=self.sensor_groups[-1].start,
                        count=self.sensor_groups[-1].count + sensor.size,
                        sensors=[*self.sensor_groups[-1].sensors, sensor],
                    )

    async def _fetch_registers(self, group: _SensorGroup) -> ReadInputRegistersResponse:
        LOGGER.debug("reading registers %d (count=%d)", group.start, group.count)
        return await self.client.read_input_registers(
            address=group.start,
            count=group.count,
            slave=1,
        )

    async def _fetch_retry(self, group: _SensorGroup) -> ReadInputRegistersResponse:
        try:
            return await self._fetch_registers(group)
        except ConnectionException:
            if not self.client.connected:
                await self.client.connect()
            return await self._fetch_registers(group)
        except asyncio.exceptions.TimeoutError:
            if not self.client.connected:
                await self.client.connect()
            return await self._fetch_registers(group)

    async def _fetch_sensors(self, group: _SensorGroup) -> dict[str, any] | None:
        LOGGER.debug("fetching registers from %d (count=%d)", group.start, group.count)

        try:
            result = await self._fetch_retry(group)
        except ModbusException as exception:
            LOGGER.error(
                "Failed to fetch registers for group %d (count=%d): %s",
                group.start,
                group.count,
                exception,
            )
            return None

        if result.isError():
            LOGGER.error(
                "Failed to fetch registers for group %d (count=%d): %s",
                group.start,
                group.count,
                result,
            )
            return None

        LOGGER.debug("got registers %d", group.start)

        def decode_single(
            sensor: BaseSensorAddress,
            result: ReadInputRegistersResponse,
        ):
            try:
                available, value = sensor.decode(
                    BinaryPayloadDecoder.fromRegisters(
                        result.registers,
                        byteorder=Endian.BIG,
                        wordorder=Endian.LITTLE,
                    )
                )
                if available:
                    data[sensor.name] = value
            except ValueError as single_error:
                # if decoding fails (again) set to None (unknown)
                LOGGER.debug(
                    "decode failed for %s after single fetch",
                    sensor.name,
                    exc_info=single_error,
                )
                data[sensor.name] = None

        try:
            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers,
                byteorder=Endian.BIG,
                wordorder=Endian.LITTLE,
            )

            LOGGER.debug("got decoder %d", group.start)

            data: dict[str, any] = {}

            if len(group.sensors) == 1:
                # single sensor -> don't do refetch on error
                decode_single(group.sensors[0], result)
            else:
                for sensor in group.sensors:
                    try:
                        available, value = sensor.decode(decoder)
                        if available:
                            data[sensor.name] = value
                    except ValueError as error:
                        # if decoding fails refetch single register and try again
                        LOGGER.debug(
                            "decode failed for %s, retrying with single fetch",
                            sensor.name,
                            exc_info=error,
                        )

                        single_result = await self._fetch_retry(
                            IdmHeatpump._SensorGroup(
                                start=sensor.address,
                                count=sensor.size,
                                sensors=[sensor],
                            )
                        )

                        decode_single(sensor, single_result)

        except ModbusException as exception:
            LOGGER.error(
                "Failed to fetch registers for group %d (count=%d): %s",
                group.start,
                group.count,
                exception,
            )
            return None

        LOGGER.debug("decoded registers %d", group.start)

        if NAME_POWER_USAGE in data and self.max_power_usage is not None:
            reported_power_usage = data[NAME_POWER_USAGE]
            limited_power_usage = (
                reported_power_usage
                if reported_power_usage <= self.max_power_usage
                else None
            )
            data[NAME_POWER_USAGE] = limited_power_usage
            LOGGER.info(
                "power usage value limited from %.2f to %.2f",
                reported_power_usage,
                limited_power_usage,
            )

        return data

    async def async_get_data(self):
        """Get data from the heatpump."""

        if not self.client.connected:
            await self.client.connect()
            LOGGER.debug("connected")

        groups = await asyncio.gather(
            *[self._fetch_sensors(group) for group in self.sensor_groups],
            return_exceptions=True,
        )

        LOGGER.debug("got groups")

        data: dict[str, any] = {}
        for group in groups:
            if group is not None and isinstance(group, dict):
                data.update(group)

        LOGGER.debug("got data")

        return data

    async def async_write_value(self, address: BaseSensorAddress[_T], value: _T):
        """Write value to one of the addresses of this heat pump."""
        if not self.client.connected:
            await self.client.connect()
            LOGGER.debug("connected")

        builder = BinaryPayloadBuilder(
            byteorder=Endian.BIG,
            wordorder=Endian.LITTLE,
        )

        address.encode(builder, value)
        registers = builder.to_registers()
        assert len(registers) == address.size

        response: ModbusResponse = await self.client.write_registers(
            address=address.address,
            values=registers,
            slave=1,
        )
        assert not response.isError()

    @staticmethod
    async def test_hostname(hostname: str) -> bool:
        """Check if the hostname is reachable via Modbus."""
        heatpump = IdmHeatpump(
            hostname,
            circuits=[],
            zones=[],
            no_groups=True,
            max_power_usage=None,
        )
        try:
            data = await heatpump.async_get_data()
            return len(data) > 0
        except Exception:  # pylint: disable=broad-except
            return False
