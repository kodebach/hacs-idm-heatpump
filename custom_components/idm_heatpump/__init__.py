"""Custom integration to integrate idm_heatpump with Home Assistant.

For more details about this integration, please refer to
https://github.com/custom-components/idm_heatpump
"""

from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.loader import async_get_integration

from .const import (
    CONF_HOSTNAME,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DOMAIN,
    ISSUE_URL,
    NAME,
    OPT_HEATING_CIRCUITS,
    OPT_MAX_POWER_USAGE,
    OPT_READ_WITHOUT_GROUPS,
    OPT_REFRESH_INTERVAL,
    OPT_REQUEST_TIMEOUT,
    OPT_ZONE_COUNT,
    OPT_ZONE_ROOM_9_RELAY,
    OPT_ZONE_ROOM_COUNT,
    STARTUP_MESSAGE_TEMPLATE,
)
from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .idm_heatpump import IdmHeatpump
from .logger import LOGGER
from .sensor_addresses import HeatingCircuit, ZoneModule

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    integration = await async_get_integration(hass, DOMAIN)

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    LOGGER.info(
        STARTUP_MESSAGE_TEMPLATE,
        NAME,
        integration.manifest["version"],
        ISSUE_URL,
    )

    hostname = entry.data.get(CONF_HOSTNAME)
    zone_count = entry.options.get(OPT_ZONE_COUNT, 0)
    max_power_usage = entry.options.get(OPT_MAX_POWER_USAGE, 0.0)

    heatpump = IdmHeatpump(
        hostname=hostname,
        circuits=[
            HeatingCircuit[c] for c in entry.options.get(OPT_HEATING_CIRCUITS, [])
        ],
        zones=[
            ZoneModule(
                index=i,
                room_count=entry.options.get(OPT_ZONE_ROOM_COUNT[i], 1),
                room_9_relay=entry.options.get(OPT_ZONE_ROOM_9_RELAY[i], False),
            )
            for i in range(zone_count)
        ],
        no_groups=entry.options.get(OPT_READ_WITHOUT_GROUPS, False),
        max_power_usage=max_power_usage if max_power_usage != 0.0 else None,
    )

    update_interval = timedelta(
        **entry.options.get(OPT_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
    )
    timeout_delta = timedelta(
        **entry.options.get(OPT_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT)
    )
    LOGGER.debug(
        "Setting up IDM heat pump at %s with update_interval=%s",
        hostname,
        update_interval,
    )
    coordinator = IdmHeatpumpDataUpdateCoordinator(
        hass,
        heatpump=heatpump,
        update_interval=update_interval,
        timeout_delta=timeout_delta,
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
        coordinator: IdmHeatpumpDataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ]

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


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        old_refresh = max(
            60,
            config_entry.options.get(OPT_REFRESH_INTERVAL, 0),
        )

        new_options = {
            OPT_REFRESH_INTERVAL: {
                "hours": old_refresh // 3600,
                "minutes": (old_refresh % 3600) // 60,
                "seconds": old_refresh % 60,
            }
        }

        config_entry.version = 2
        hass.config_entries.async_update_entry(
            config_entry,
            options=new_options,
        )
        persistent_notification.async_create(
            hass,
            (
                "The IDM heat pump integration has been updated. Please go to the integrations page"
                " and re-configure to re-enable sensors for heat circuits and zone modules."
            ),
            "IDM heat pump migration",
        )
        return True

    LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
