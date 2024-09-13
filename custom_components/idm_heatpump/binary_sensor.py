"""Binary sensor platform for idm_heatpump."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SERVICE_SET_BINARY,
    SensorFeatures,
)
from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .entity import IdmHeatpumpEntity
from .logger import LOGGER
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

    platform = entity_platform.async_get_current_platform()

    async def handle_set_binary(call: ServiceCall):
        target = call.data.get("target")
        entity = platform.entities[target]

        if (
            not isinstance(entity, IdmHeatpumpEntity)
            or SensorFeatures.SET_BINARY not in entity.supported_features
        ):
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support this service.",
                translation_domain=DOMAIN,
                translation_key="entity_not_supported",
                translation_placeholders={
                    "entity_id": entity.entity_id,
                },
            )

        entity: IdmHeatpumpEntity[bool]

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError(
                f"Must acknowledge risk to call {SERVICE_SET_BINARY}",
                translation_domain=DOMAIN,
                translation_key="risk_not_acknowledged",
            )

        value: bool = call.data.get("value")
        LOGGER.debug(
            "Calling %s with value %s on %s",
            SERVICE_SET_BINARY,
            value,
            entity.entity_id,
        )
        await entity.async_write_value(value)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_BINARY,
        service_func=handle_set_binary,
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
