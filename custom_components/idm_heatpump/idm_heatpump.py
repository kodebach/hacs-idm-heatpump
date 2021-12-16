"""Abstraction over the modbus interface of IDM heatpumps"""

from dataclasses import dataclass
import collections
from typing import List


from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus.register_read_message import ReadInputRegistersResponse

from .logger import LOGGER
from .sensor import IdmHeatpumpSensor
from .sensor_addresses import SENSOR_ADDRESSES, IdmSensorAddress


class IdmHeatpump:
    """Abstraction over the modbus interface of IDM heatpumps"""

    client: ModbusTcpClient
    sensors: List[IdmHeatpumpSensor]

    def __init__(self, hostname: str) -> None:
        # TODO: asyncio
        self.client = ModbusTcpClient(host=hostname)

        self.sensors: List[IdmSensorAddress] = sorted(
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

    async def async_get_data(self):
        """Get data from the heatpump"""

        @dataclass
        class _SensorGroup:
            start: int
            count: int
            sensors: List[IdmSensorAddress]

        sensor_groups: List[_SensorGroup] = []
        for sensor in self.sensors:
            if (
                len(sensor_groups) == 0
                or sensor.address != sensor_groups[-1].start + sensor_groups[-1].count
            ):
                sensor_groups.append(
                    _SensorGroup(
                        start=sensor.address, count=sensor.size, sensors=[sensor]
                    )
                )
            else:
                sensor_groups[-1] = _SensorGroup(
                    start=sensor_groups[-1].start,
                    count=sensor_groups[-1].count + sensor.size,
                    sensors=[*sensor_groups[-1].sensors, sensor],
                )

        data = {}
        self.client.connect()
        for group in sensor_groups:

            def fetch_register(group: _SensorGroup) -> ReadInputRegistersResponse:
                return self.client.read_input_registers(
                    address=group.start,
                    count=group.count,
                    unit=1,
                )

            try:
                try:
                    result = fetch_register(group)
                except ConnectionException:
                    self.client.connect()
                    result = fetch_register(group)
            except ModbusException as exception:
                LOGGER.error(
                    "Failed to fetch registers for group %s: %s", group, exception
                )
                continue

            if result.isError():
                LOGGER.error(
                    "Failed to fetch registers for group %s: %s", group, result
                )
                continue

            try:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    result.registers,
                    byteorder=Endian.Big,
                    wordorder=Endian.Little,
                )

                for sensor in group.sensors:
                    data[sensor.name] = sensor.decode(decoder)
            except ModbusException as exception:
                LOGGER.error(
                    "Failed to fetch registers for group %s: %s", group, exception
                )
                continue

        self.client.close()

        return data

    @staticmethod
    def test_hostname(hostname: str) -> bool:
        """Check if the hostname is reachable via Modbus"""
        # TODO: actually check
        return len(hostname) > 0
