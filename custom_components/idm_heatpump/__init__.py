"""Custom integration to integrate idm_heatpump with Home Assistant.

For more details about this integration, please refer to
https://github.com/custom-components/idm_heatpump
"""
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .idm_heatpump import IdmHeatpump
from .logger import LOGGER

import async_timeout

from .const import (
    CONF_HOSTNAME,
    DOMAIN,
    OPT_REFRESH_INTERVAL,
    PLATFORMS,
    STARTUP_MESSAGE,
)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        LOGGER.info(STARTUP_MESSAGE)

    hostname = entry.data.get(CONF_HOSTNAME)

    heatpump = IdmHeatpump(hostname=hostname)

    update_interval = timedelta(seconds=entry.options.get(OPT_REFRESH_INTERVAL, 300))
    LOGGER.debug(
        f"Setting up IDM heat pump at {hostname} with update_interval={update_interval}"
    )
    coordinator = IdmHeatpumpDataUpdateCoordinator(
        hass,
        heatpump=heatpump,
        update_interval=update_interval,
    )
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


class IdmHeatpumpDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
