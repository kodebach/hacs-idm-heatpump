"""Sensor platform for idm_heatpump."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .sensor_addresses import (
    SENSOR_ADDRESSES,
    IdmSensorAddress,
)
from .const import DOMAIN
from .entity import IdmHeatpumpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IdmHeatpumpSensor(
                coordinator,
                entry,
                sensor_name=name,
            )
            for name, _ in SENSOR_ADDRESSES.items()
        ],
    )


class IdmHeatpumpSensor(IdmHeatpumpEntity, SensorEntity):
    """IDM heatpump sensor class."""

    sensor_address: IdmSensorAddress

    def __init__(self, coordinator, config_entry, sensor_name: str):
        """Create sensor."""
        super().__init__(coordinator, config_entry)
        if sensor_name not in SENSOR_ADDRESSES:
            raise Exception(f"Sensor not found: {sensor_name}")

        self.sensor_address = SENSOR_ADDRESSES[sensor_name]
        self.entity_description = self.sensor_address.entity_description(config_entry)

    @property
    def sensor_id(self):
        """Return sensor id."""
        return self.sensor_address.name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.sensor_address.name)
