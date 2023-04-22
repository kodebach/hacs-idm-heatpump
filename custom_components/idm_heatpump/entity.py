"""IdmHeatpumpEntity class."""
from abc import abstractmethod
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_DISPLAY_NAME, CONF_HOSTNAME, DOMAIN, MANUFACTURER


class IdmHeatpumpEntity(CoordinatorEntity):
    """IdmHeatpumpEntity."""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry

    @property
    @abstractmethod
    def sensor_id(self) -> str:
        """Return the unique ID for this sensor."""

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{slugify(self.config_entry.data.get(CONF_HOSTNAME))}_{self.sensor_id}"

    @property
    def device_info(self):
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.config_entry.entry_id)},
            ATTR_NAME: self.config_entry.data.get(CONF_DISPLAY_NAME),
            ATTR_MODEL: "Navigator 2.0",
            ATTR_MANUFACTURER: MANUFACTURER,
        }

    @property
    def extra_state_attributes(self):
        return {
            "integration": DOMAIN,
        }
