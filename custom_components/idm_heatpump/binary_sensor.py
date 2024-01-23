"""Binary sensor platform for idm_heatpump."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
)
from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .entity import IdmHeatpumpEntity
from .sensor_addresses import IdmBinarySensorAddress


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up binary_sensor platform."""
    coordinator: IdmHeatpumpDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IdmHeatpumpBinarySensor(coordinator, entry, address)
            for address in coordinator.heatpump.sensors
            if isinstance(address, IdmBinarySensorAddress)
        ]
    )


class IdmHeatpumpBinarySensor(IdmHeatpumpEntity, BinarySensorEntity):
    """IDM heatpump binary sensor class."""

    def __init__(
        self,
        coordinator: IdmHeatpumpDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_address: IdmBinarySensorAddress,
    ):
        """Create binary sensor."""
        super().__init__(coordinator, config_entry)

        self.sensor_address = sensor_address
        self.entity_description = self.sensor_address.entity_description(config_entry)

    @property
    def sensor_id(self):
        """Return sensor id."""
        return self.sensor_address.name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.sensor_address.name)
