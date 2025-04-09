"""Coordinator for idm_heatpump."""

from asyncio import timeout
from datetime import timedelta
from typing import TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator

from .const import DOMAIN
from .idm_heatpump import IdmHeatpump
from .logger import LOGGER
from .sensor_addresses import BaseSensorAddress

_T = TypeVar("_T")


class IdmHeatpumpDataUpdateCoordinator(TimestampDataUpdateCoordinator[dict[str, any]]):
    """Class to manage fetching data from the API."""

    heatpump: IdmHeatpump
    timeout_delta: timedelta

    def __init__(
        self,
        hass: HomeAssistant,
        heatpump: IdmHeatpump,
        update_interval: timedelta,
        timeout_delta: timedelta,
    ) -> None:
        """Initialize."""
        self.heatpump = heatpump
        self.timeout_delta = timeout_delta
        self.platforms = []

        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            async with timeout(self.timeout_delta.total_seconds()):
                has_error, data = await self.heatpump.async_get_data()
                if has_error:
                    LOGGER.error("update partially failed")
                return data
        except TimeoutError as e:
            LOGGER.error("timeout while updating")
            raise e
        except Exception as exception:
            raise exception

    async def async_write_value(self, address: BaseSensorAddress[_T], value: _T):
        """Update data via library."""
        try:
            async with timeout(self.timeout_delta.total_seconds()):
                await self.heatpump.async_write_value(address, value)
        except TimeoutError as e:
            LOGGER.error("timeout while writing")
            raise e
        except Exception as exception:
            raise exception

        self.data[address.name] = value
