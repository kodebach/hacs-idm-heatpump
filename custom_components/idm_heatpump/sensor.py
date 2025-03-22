"""Sensor platform for idm_heatpump."""

from collections.abc import Callable
from typing import Any, TypeVar

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pymodbus.client.mixin import ModbusClientMixin

from .const import (
    DOMAIN,
    SERVICE_SET_BATTERY,
    SERVICE_SET_CIRCUIT_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_POWER,
    SERVICE_SET_ROOM_MODE,
    SERVICE_SET_SYSTEM_STATUS,
    SERVICE_SET_TEMPERATURE,
    CircuitMode,
    RoomMode,
    SensorFeatures,
    SystemStatus,
)
from .coordinator import IdmHeatpumpDataUpdateCoordinator
from .entity import IdmHeatpumpEntity
from .logger import LOGGER
from .sensor_addresses import IdmSensorAddress

_T = TypeVar("_T")


def _register_set_service(
    hass: HomeAssistant,
    service: str,
    feature: SensorFeatures,
    convert_value: Callable[[Any | None, IdmHeatpumpEntity], _T],
):
    async def handle_set(call: ServiceCall):
        platform = entity_platform.async_get_current_platform()

        target = call.data.get("target")
        entity = platform.entities[target]

        if (
            not isinstance(entity, IdmHeatpumpEntity)
            or feature not in entity.supported_features
        ):
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support this service.",
                translation_domain=DOMAIN,
                translation_key="entity_not_supported",
                translation_placeholders={
                    "entity_id": entity.entity_id,
                },
            )

        entity: IdmHeatpumpEntity

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError(
                f"Must acknowledge risk to call {service}",
                translation_domain=DOMAIN,
                translation_key="risk_not_acknowledged",
            )

        raw_value = call.data.get("value")
        value = convert_value(raw_value, entity)

        if value is None:
            raise HomeAssistantError(f"invalid value: {raw_value}")

        LOGGER.debug(
            "Calling %s with value %s on %s",
            service,
            value,
            entity.entity_id,
        )
        await entity.async_write_value(value)

    hass.services.async_register(
        domain=DOMAIN,
        service=service,
        service_func=handle_set,
    )


def _convert_temperature(value: Any | None, entity: IdmHeatpumpEntity) -> float | int:
    value = float(value)
    if entity.sensor_address.datatype != ModbusClientMixin.DATATYPE.FLOAT32:
        if int(value) != value:
            raise HomeAssistantError(
                f"Must be integer value to use {SERVICE_SET_TEMPERATURE} on {entity.entity_id}",
                translation_domain=DOMAIN,
                translation_key="integer_required",
                translation_placeholders={
                    "entity_id": entity.entity_id,
                },
            )

        value = int(value)


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

    _register_set_service(
        hass,
        SERVICE_SET_POWER,
        SensorFeatures.SET_POWER,
        float,
    )
    _register_set_service(
        hass,
        SERVICE_SET_BATTERY,
        SensorFeatures.SET_BATTERY,
        int,
    )
    _register_set_service(
        hass,
        SERVICE_SET_TEMPERATURE,
        SensorFeatures.SET_TEMPERATURE,
        _convert_temperature,
    )
    _register_set_service(
        hass,
        SERVICE_SET_HUMIDITY,
        SensorFeatures.SET_HUMIDITY,
        float,
    )
    _register_set_service(
        hass,
        SERVICE_SET_ROOM_MODE,
        SensorFeatures.SET_ROOM_MODE,
        lambda v: RoomMode[v],
    )
    _register_set_service(
        hass,
        SERVICE_SET_CIRCUIT_MODE,
        SensorFeatures.SET_CIRCUIT_MODE,
        lambda v: CircuitMode[v],
    )
    _register_set_service(
        hass,
        SERVICE_SET_SYSTEM_STATUS,
        SensorFeatures.SET_SYSTEM_STATUS,
        lambda v: SystemStatus[v],
    )

    async def handle_set_temperature(call: ServiceCall):
        target = call.data.get("target")
        entity = platform.entities[target]

        if (
            not isinstance(entity, IdmHeatpumpEntity)
            or SensorFeatures.SET_TEMPERATURE not in entity.supported_features
        ):
            raise HomeAssistantError(
                f"Entity {entity.entity_id} does not support this service.",
                translation_domain=DOMAIN,
                translation_key="entity_not_supported",
                translation_placeholders={
                    "entity_id": entity.entity_id,
                },
            )

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError(
                f"Must acknowledge risk to call {SERVICE_SET_TEMPERATURE}",
                translation_domain=DOMAIN,
                translation_key="risk_not_acknowledged",
            )

        entity: IdmHeatpumpEntity[int | float]

        value: float = call.data.get("value")

        if entity.sensor_address.datatype != ModbusClientMixin.DATATYPE.FLOAT32:
            if int(value) != value:
                raise HomeAssistantError(
                    f"Must be integer value to use {SERVICE_SET_TEMPERATURE} on {entity.entity_id}",
                    translation_domain=DOMAIN,
                    translation_key="integer_required",
                    translation_placeholders={
                        "entity_id": entity.entity_id,
                    },
                )

            value = int(value)

        LOGGER.debug(
            "Calling %s with value %s on %s",
            SERVICE_SET_TEMPERATURE,
            value,
            entity.entity_id,
        )
        await entity.async_write_value(value)

    hass.services.async_register(
        domain=DOMAIN,
        service=SERVICE_SET_TEMPERATURE,
        service_func=handle_set_temperature,
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
