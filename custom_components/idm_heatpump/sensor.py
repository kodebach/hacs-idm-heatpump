"""Sensor platform for idm_heatpump."""

from typing import Any, TypeVar

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, HomeAssistantError
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
from .sensor_addresses import IdmSensorAddress
from .services import register_set_service

_T = TypeVar("_T")


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

    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_POWER,
        SensorFeatures.SET_POWER,
        lambda v, _: float(v),
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_BATTERY,
        SensorFeatures.SET_BATTERY,
        lambda v, _: int(v),
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_TEMPERATURE,
        SensorFeatures.SET_TEMPERATURE,
        _convert_temperature,
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_HUMIDITY,
        SensorFeatures.SET_HUMIDITY,
        lambda v, _: float(v),
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_ROOM_MODE,
        SensorFeatures.SET_ROOM_MODE,
        lambda v, _: RoomMode[v],
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_CIRCUIT_MODE,
        SensorFeatures.SET_CIRCUIT_MODE,
        lambda v, _: CircuitMode[v],
    )
    register_set_service(
        Platform.SENSOR,
        hass,
        SERVICE_SET_SYSTEM_STATUS,
        SensorFeatures.SET_SYSTEM_STATUS,
        lambda v, _: SystemStatus[v],
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
