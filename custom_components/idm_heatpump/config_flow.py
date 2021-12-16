"""Adds config flow for Blueprint."""
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .idm_heatpump import IdmHeatpump

from .const import (
    CONF_HOSTNAME,
    CONF_DISPLAY_NAME,
    DOMAIN,
    PLATFORMS,
)


class IdmHeatpumpFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for IDM heat pump."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if any(
            (
                user_input is not None
                and e.data.get(CONF_HOSTNAME) == user_input[CONF_HOSTNAME]
            )
            for e in self._async_current_entries()
        ):
            return self.async_abort(reason="hostname_in_use")

        if user_input is not None:
            valid = await self._test_hostname(user_input[CONF_HOSTNAME])
            if valid:
                return self.async_create_entry(
                    title=user_input[CONF_DISPLAY_NAME],
                    data=user_input,
                )
            else:
                self._errors["base"] = "hostname"

            return await self._show_config_form(user_input)

        user_input = {}
        user_input[CONF_DISPLAY_NAME] = ""
        user_input[CONF_HOSTNAME] = ""

        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IdmHeatpumpOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):
        """Show the configuration form to edit hostname."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DISPLAY_NAME, default=user_input[CONF_DISPLAY_NAME]
                    ): str,
                    vol.Required(CONF_HOSTNAME, default=user_input[CONF_HOSTNAME]): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_hostname(self, hostname):
        """Return true if hostname is valid."""
        try:
            return IdmHeatpump.test_hostname(hostname)
        except Exception:  # pylint: disable=broad-except
            pass
        return False


class IdmHeatpumpOptionsFlowHandler(config_entries.OptionsFlow):
    """IDM heat pump config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(x, default=self.options.get(x, True)): bool
                    for x in sorted(PLATFORMS)
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_DISPLAY_NAME), data=self.options
        )
