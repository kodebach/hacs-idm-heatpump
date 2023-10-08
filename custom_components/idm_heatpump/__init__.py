"""Custom integration to integrate idm_heatpump with Home Assistant.

For more details about this integration, please refer to
https://github.com/custom-components/idm_heatpump
"""
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant

from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .idm_heatpump import IdmHeatpump
from .logger import LOGGER

from .const import (
    CONF_HOSTNAME,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    OPT_HEATING_CIRCUITS,
    OPT_REFRESH_INTERVAL,
    PLATFORMS,
    STARTUP_MESSAGE,
)


async def async_setup(hass: HomeAssistant, config: Config):  # pylint: disable=unused-argument
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        LOGGER.info(STARTUP_MESSAGE)

    hostname = entry.data.get(CONF_HOSTNAME)

    heatpump = IdmHeatpump(
        hostname=hostname,
        circuits=entry.options.get(OPT_HEATING_CIRCUITS, []),
    )

    update_interval = timedelta(**entry.options.get(
        OPT_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL))
    LOGGER.debug("Setting up IDM heat pump at %s with update_interval=%s",
                 hostname, update_interval)
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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: IdmHeatpumpDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

        # Ensure disconnected and cleanup stop sub
        coordinator.heatpump.client.close()

        del hass.data[DOMAIN][entry.entry_id]

    if not hass.data[DOMAIN]:
        # remove services
        pass

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
