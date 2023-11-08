"""Coordinator for idm_heatpump."""
from datetime import timedelta
from typing import TypeVar
import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .idm_heatpump import IdmHeatpump
from .logger import LOGGER
from .sensor_addresses import BaseSensorAddress

_T = TypeVar("_T")


class IdmHeatpumpDataUpdateCoordinator(DataUpdateCoordinator[dict[str, any]]):
    """Class to manage fetching data from the API."""

    heatpump: IdmHeatpump

    def __init__(
        self, hass: HomeAssistant, heatpump: IdmHeatpump, update_interval: timedelta
    ) -> None:
        """Initialize."""
        self.heatpump = heatpump
        self.platforms = []

        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        async with async_timeout.timeout(10):
            try:
                return await self.heatpump.async_get_data()
            except Exception as exception:
                LOGGER.exception("error")
                raise UpdateFailed() from exception

    async def async_write_value(self, address: BaseSensorAddress[_T], value: _T):
        """Update data via library."""
        async with async_timeout.timeout(10):
            try:
                return await self.heatpump.async_write_value(address, value)
            except Exception as exception:
                LOGGER.exception("error")
                raise exception
