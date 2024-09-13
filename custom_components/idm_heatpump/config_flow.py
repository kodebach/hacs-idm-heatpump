"""Adds config flow for Blueprint."""

from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config import cv
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import UnitOfPower
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_DISPLAY_NAME,
    CONF_HOSTNAME,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REQUEST_TIMEOUT,
    DOMAIN,
    MAX_ROOM_COUNT,
    MAX_ZONE_COUNT,
    MIN_REFRESH_INTERVAL,
    OPT_HEATING_CIRCUITS,
    OPT_MAX_POWER_USAGE,
    OPT_READ_WITHOUT_GROUPS,
    OPT_REFRESH_INTERVAL,
    OPT_REQUEST_TIMEOUT,
    OPT_ZONE_COUNT,
    OPT_ZONE_ROOM_9_RELAY,
    OPT_ZONE_ROOM_COUNT,
)
from .idm_heatpump import IdmHeatpump
from .sensor_addresses import HeatingCircuit


class IdmHeatpumpFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for IDM heat pump."""

    VERSION = 2

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._data = {}
        self._options = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DISPLAY_NAME,
                    default=self._data.get(CONF_DISPLAY_NAME, ""),
                ): str,
                vol.Required(
                    CONF_HOSTNAME,
                    default=self._data.get(CONF_HOSTNAME, ""),
                ): str,
            }
        )

        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOSTNAME])
            self._abort_if_unique_id_configured()

            self._data.update(user_input)

            valid = await self._test_hostname(user_input[CONF_HOSTNAME])
            if not valid:
                errors[CONF_HOSTNAME] = "hostname"

            if len(errors) == 0:
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_options(self, user_input=None):
        """Step to configure options."""

        result = _async_step_base_options(self._options, user_input)
        if result is None:
            return await self.async_step_zones(user_input)

        [schema, errors] = result

        return self.async_show_form(
            step_id="options",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_zones(self, user_input=None):
        """Handle a flow for zones."""
        result = _async_step_zone_options(self._options, user_input)
        if result is None:
            return self.async_create_entry(
                title=self._data[CONF_DISPLAY_NAME],
                data=self._data,
                options=self._options,
            )

        [schema, errors] = result

        return self.async_show_form(
            step_id="zones",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Return options flow."""
        return IdmHeatpumpOptionsFlowHandler(config_entry)

    async def _test_hostname(self, hostname):
        """Return true if hostname is valid."""
        try:
            return await IdmHeatpump.test_hostname(hostname)
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class IdmHeatpumpOptionsFlowHandler(OptionsFlow):
    """IDM heat pump config flow options handler."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input=None):
        """Step to configure options."""
        result = _async_step_base_options(self.options, user_input)
        if result is None:
            return await self.async_step_zones(user_input)

        [schema, errors] = result

        return self.async_show_form(
            step_id="options",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_zones(self, user_input=None):
        """Handle a flow for zones."""
        result = _async_step_zone_options(self.options, user_input)
        if result is None:
            return self.async_create_entry(
                title=f"{self.config_entry.data.get(CONF_DISPLAY_NAME)} - Zones",
                data=self.options,
            )

        [schema, errors] = result

        return self.async_show_form(
            step_id="zones",
            data_schema=schema,
            errors=errors,
        )


def _async_step_base_options(
    options: dict[str, Any],
    user_input=None,
) -> tuple[vol.Schema, dict[str, str]] | None:
    schema = vol.Schema(
        {
            vol.Required(
                OPT_REFRESH_INTERVAL,
                default=options.get(OPT_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            ): vol.All(selector({"duration": {}})),
            vol.Required(
                OPT_REQUEST_TIMEOUT,
                default=options.get(OPT_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
            ): vol.All(selector({"duration": {}})),
            vol.Required(
                OPT_HEATING_CIRCUITS,
                default=options.get(OPT_HEATING_CIRCUITS, []),
            ): vol.All(
                selector(
                    {
                        "select": {
                            "options": [c.name for c in HeatingCircuit],
                            "multiple": True,
                        }
                    }
                ),
                vol.Length(min=1, msg="Select at least one"),
            ),
            vol.Required(
                OPT_ZONE_COUNT,
                default=options.get(OPT_ZONE_COUNT, 0),
            ): vol.All(
                selector(
                    {
                        "number": {
                            "min": 0,
                            "max": MAX_ZONE_COUNT,
                        }
                    }
                ),
                cv.positive_int,
            ),
            vol.Required(
                OPT_READ_WITHOUT_GROUPS,
                default=options.get(OPT_READ_WITHOUT_GROUPS, False),
            ): bool,
            vol.Optional(
                OPT_MAX_POWER_USAGE,
                default=options.get(OPT_MAX_POWER_USAGE, 0.0),
            ): selector(
                {
                    "number": {
                        # "min": 0,
                        "step": "any",
                        "mode": "box",
                        "unit_of_measurement": UnitOfPower.KILO_WATT,
                    }
                }
            ),
        }
    )

    errors = {}

    if user_input is not None:
        options.update(user_input)

        if timedelta(**options[OPT_REFRESH_INTERVAL]) < timedelta(
            **MIN_REFRESH_INTERVAL
        ):
            errors[OPT_REFRESH_INTERVAL] = "min_refresh_interval"

        if timedelta(**options[OPT_REFRESH_INTERVAL]) < timedelta(
            **options[OPT_REQUEST_TIMEOUT]
        ):
            errors[OPT_REQUEST_TIMEOUT] = "request_refresh_interval"

        if len(errors) == 0:
            return None

    return [schema, errors]


def _async_step_zone_options(
    options: dict[str, Any],
    user_input=None,
) -> tuple[vol.Schema, dict[str, str]] | None:
    zone_count: int = options[OPT_ZONE_COUNT]

    schema = vol.Schema(
        dict(
            field
            for zone in range(zone_count)
            for field in [
                (
                    vol.Required(
                        OPT_ZONE_ROOM_COUNT[zone],
                        default=options.get(OPT_ZONE_ROOM_COUNT[zone], 1),
                    ),
                    vol.All(
                        selector(
                            {
                                "number": {
                                    "min": 1,
                                    "max": MAX_ROOM_COUNT,
                                }
                            }
                        ),
                        cv.positive_int,
                    ),
                ),
                (
                    vol.Required(
                        OPT_ZONE_ROOM_9_RELAY[zone],
                        default=options.get(OPT_ZONE_ROOM_9_RELAY[zone], False),
                    ),
                    bool,
                ),
            ]
        )
    )

    errors = {}

    if user_input is not None and all(
        OPT_ZONE_ROOM_COUNT[zone] in user_input for zone in range(zone_count)
    ):
        options.update(user_input)

        if len(errors) == 0:
            return None

    return [schema, errors]
