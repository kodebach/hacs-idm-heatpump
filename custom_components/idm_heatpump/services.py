"""Helpers for services."""

from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall
from homeassistant.helpers import entity_platform

from .const import (
    DOMAIN,
    SensorFeatures,
)
from .entity import IdmHeatpumpEntity
from .logger import LOGGER

_T = TypeVar("_T")


async def _handle_set(
    platform_domain: str,
    hass: HomeAssistant,
    service: str,
    feature: SensorFeatures,
    convert_value: Callable[[Any | None, IdmHeatpumpEntity], _T],
    call: ServiceCall,
):
    platform = None
    for p in entity_platform.async_get_platforms(hass, DOMAIN):
        if p.domain == platform_domain:
            platform = p

    if platform is None:
        raise HomeAssistantError(f"Platform {platform} not found for {DOMAIN}")

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


def register_set_service(
    platform: str,
    hass: HomeAssistant,
    service: str,
    feature: SensorFeatures,
    convert_value: Callable[[Any | None, IdmHeatpumpEntity], _T],
):
    """Register a service for setting a register."""

    hass.services.async_register(
        domain=DOMAIN,
        service=service,
        service_func=partial(
            _handle_set,
            platform,
            hass,
            service,
            feature,
            convert_value,
        ),
    )
