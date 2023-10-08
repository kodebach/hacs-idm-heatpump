"""Adds config flow for Blueprint."""
from datetime import timedelta
from typing import Any
from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
import voluptuous as vol


from .idm_heatpump import IdmHeatpump
from .sensor_addresses import HeatingCircuit

from .const import (
    CONF_HOSTNAME,
    CONF_DISPLAY_NAME,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    MIN_REFRESH_INTERVAL,
    OPT_HEATING_CIRCUITS,
    OPT_REFRESH_INTERVAL,
)


class IdmHeatpumpFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for IDM heat pump."""

    VERSION = 1

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
        """Step to configure options during setup."""

        result = _async_step_options(self._options, user_input)
        if result is None:
            return self.async_create_entry(
                title=self._data[CONF_DISPLAY_NAME],
                data=self._data,
                options=self._options,
            )

        [schema, errors] = result

        return self.async_show_form(
            step_id="options",
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
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        result = _async_step_options(self.options, user_input)
        if result is None:
            return self.async_create_entry(
                title=self.config_entry.data.get(CONF_DISPLAY_NAME),
                data=self.options,
            )

        [schema, errors] = result

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


def _async_step_options(
    options: dict[str, Any],
    user_input=None,
) -> tuple[vol.Schema, dict[str, str]] | None:
    schema = vol.Schema(
        {
            vol.Required(
                OPT_REFRESH_INTERVAL,
                default=options.get(
                    OPT_REFRESH_INTERVAL,
                    DEFAULT_REFRESH_INTERVAL
                ),
            ): vol.All(selector({"duration": {}})),
            vol.Required(
                OPT_HEATING_CIRCUITS,
                default=options.get(
                    OPT_HEATING_CIRCUITS,
                    []
                ),
            ): vol.All(
                selector({"select": {
                    "options": [c.name for c in HeatingCircuit],
                    "multiple": True,
                }}),
                vol.Length(min=1, msg="Select at least one"),
            ),
        }
    )

    errors = {}

    if user_input is not None:
        options.update(user_input)

        if timedelta(**options[OPT_REFRESH_INTERVAL]) < timedelta(**MIN_REFRESH_INTERVAL):
            errors[OPT_REFRESH_INTERVAL] = "min_refresh_interval"

        if len(errors) == 0:
            return None

    return [schema, errors]
