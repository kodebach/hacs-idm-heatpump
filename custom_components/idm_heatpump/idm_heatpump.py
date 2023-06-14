"""Abstraction over the modbus interface of IDM heatpumps."""

import asyncio
from dataclasses import dataclass
import collections
from typing import Union

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus.register_read_message import ReadInputRegistersResponse

from custom_components.idm_heatpump.logger import LOGGER
from custom_components.idm_heatpump.sensor import IdmHeatpumpSensor
from custom_components.idm_heatpump.sensor_addresses import (
    SENSOR_ADDRESSES,
    IdmSensorAddress,
)


class IdmHeatpump:
    """Abstraction over the modbus interface of IDM heatpumps."""

    @dataclass
    class _SensorGroup:
        start: int
        count: int
        sensors: list[IdmSensorAddress]

    client: AsyncModbusTcpClient
    sensors: list[IdmHeatpumpSensor]
    sensor_groups: list[_SensorGroup] = []

    def __init__(self, hostname: str) -> None:
        """Create heatpump."""
        self.client = AsyncModbusTcpClient(host=hostname)

        self.sensors: list[IdmSensorAddress] = sorted(
            SENSOR_ADDRESSES.values(), key=lambda s: s.address
        )

        addresses = [s.address for s in self.sensors]
        duplicate_addresses = [
            address
            for address, count in collections.Counter(addresses).items()
            if count > 1
        ]
        if len(duplicate_addresses) > 0:
            raise Exception(f"duplicate address(es) detected: {duplicate_addresses}")

        for sensor in self.sensors:
            last_address = (
                None
                if len(self.sensor_groups) == 0
                else self.sensor_groups[-1].start + self.sensor_groups[-1].count
            )
            if len(self.sensor_groups) == 0 or sensor.address != last_address:
                self.sensor_groups.append(
                    IdmHeatpump._SensorGroup(
                        start=sensor.address, count=sensor.size, sensors=[sensor]
                    )
                )
            else:
                self.sensor_groups[-1] = IdmHeatpump._SensorGroup(
                    start=self.sensor_groups[-1].start,
                    count=self.sensor_groups[-1].count + sensor.size,
                    sensors=[*self.sensor_groups[-1].sensors, sensor],
                )

    async def _fetch_registers(self, group: _SensorGroup) -> ReadInputRegistersResponse:
        LOGGER.debug("reading registers %d", group.start)
        return await self.client.read_input_registers(
            address=group.start,
            count=group.count,
            slave=1,
        )

    async def _fetch_sensors(self, group: _SensorGroup) -> Union[dict, None]:
        LOGGER.debug("fetching registers %d", group.start)

        try:
            try:
                result = await self._fetch_registers(group)
            except ConnectionException:
                if not self.client.connected:
                    await self.client.connect()
                result = await self._fetch_registers(group)
            except asyncio.exceptions.TimeoutError:
                if not self.client.connected:
                    await self.client.connect()
                result = await self._fetch_registers(group)
        except ModbusException as exception:
            LOGGER.error(
                "Failed to fetch registers for group %d: %s", group.start, exception
            )
            return None

        if result.isError():
            LOGGER.error(
                "Failed to fetch registers for group %d: %s", group.start, result
            )
            return None

        LOGGER.debug("got registers %d", group.start)

        try:
            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers,
                byteorder=Endian.Big,
                wordorder=Endian.Little,
            )

            LOGGER.debug("got decoder %d", group.start)

            data = {}
            for sensor in group.sensors:
                data[sensor.name] = sensor.decode(decoder)
        except ModbusException as exception:
            LOGGER.error(
                "Failed to fetch registers for group %d: %s", group.start, exception
            )
            return None

        LOGGER.debug("decoded registers %d", group.start)

        return data

    async def async_get_data(self):
        """Get data from the heatpump."""

        if not self.client.connected:
            await self.client.connect()

        LOGGER.debug("connected")

        groups = await asyncio.gather(
            *[self._fetch_sensors(group) for group in self.sensor_groups]
        )

        LOGGER.debug("got groups")

        data = {}
        for group in groups:
            if group is not None:
                data.update(group)

        LOGGER.debug("got data")

        return data

    @staticmethod
    async def test_hostname(hostname: str) -> bool:
        """Check if the hostname is reachable via Modbus."""
        heatpump = IdmHeatpump(hostname)
        try:
            data = await heatpump.async_get_data()
            return len(data) > 0
        except Exception:  # pylint: disable=broad-except
            return False
