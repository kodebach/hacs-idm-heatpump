"""Binary sensor platform for idm_heatpump."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.idm_heatpump.sensor_addresses import (
    BINARY_SENSOR_ADDRESSES,
    IdmBinarySensorAddress,
)

from .const import (
    DOMAIN,
)
from .entity import IdmHeatpumpEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IdmHeatpumpBinarySensor(
                coordinator,
                entry,
                sensor_name=name,
            )
            for name, s in BINARY_SENSOR_ADDRESSES.items()
        ]
    )


class IdmHeatpumpBinarySensor(IdmHeatpumpEntity, BinarySensorEntity):
    """IDM heatpump binary sensor class."""

    sensor_address: IdmBinarySensorAddress

    def __init__(self, coordinator, config_entry, sensor_name: str):
        """Create binary sensor."""
        super().__init__(coordinator, config_entry)
        if sensor_name not in BINARY_SENSOR_ADDRESSES:
            raise Exception(f"Binary Sensor not found: {sensor_name}")

        self.sensor_address = BINARY_SENSOR_ADDRESSES[sensor_name]
        self.entity_description = self.sensor_address.entity_description(
            config_entry
        )

    @property
    def sensor_id(self):
        """Return sensor id."""
        return self.sensor_address.name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.sensor_address.name)
