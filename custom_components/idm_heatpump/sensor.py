"""Sensor platform for idm_heatpump."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_SET_BATTERY, SERVICE_SET_POWER, SensorFeatures
from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .entity import IdmHeatpumpEntity
from .logger import LOGGER
from .sensor_addresses import IdmSensorAddress


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator: IdmHeatpumpDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IdmHeatpumpSensor(coordinator, entry, address)
            for address in coordinator.heatpump.sensors
            if isinstance(address, IdmSensorAddress)
        ],
    )

    platform = entity_platform.async_get_current_platform()

    async def handle_set_power(call: ServiceCall):
        target = call.data.get("target")
        entity = platform.entities[target]

        if (
            not isinstance(entity, IdmHeatpumpEntity)
            or SensorFeatures.SET_POWER not in entity.supported_features
        ):
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support this service."
            )

        entity: IdmHeatpumpEntity[float]

        value: float = call.data.get("value")
        LOGGER.debug("Calling set_power with value %s on %s", value, entity.entity_id)
        await entity.async_write_value(value)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_POWER,
        service_func=handle_set_power,
    )

    async def handle_set_battery(call: ServiceCall):
        target = call.data.get("target")
        entity = platform.entities[target]

        if (
            not isinstance(entity, IdmHeatpumpEntity)
            or SensorFeatures.SET_BATTERY not in entity.supported_features
        ):
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support this service."
            )

        entity: IdmHeatpumpEntity[int]

        value: int = call.data.get("value")
        LOGGER.debug("Calling set_battery with value %s on %s", value, entity.entity_id)
        await entity.async_write_value(value)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_BATTERY,
        service_func=handle_set_battery,
    )


class IdmHeatpumpSensor(IdmHeatpumpEntity, SensorEntity):
    """IDM heatpump sensor class."""

    def __init__(
        self,
        coordinator: IdmHeatpumpDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_address: IdmSensorAddress,
    ):
        """Create sensor."""
        super().__init__(coordinator, config_entry)
        self.sensor_address = sensor_address
        self.entity_description = self.sensor_address.entity_description(config_entry)

    @property
    def sensor_id(self):
        """Return sensor id."""
        return self.sensor_address.name

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.sensor_address.name)
