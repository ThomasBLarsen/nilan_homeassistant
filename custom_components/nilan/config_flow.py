import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN

class NilanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Nilan configuration flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="Nilan Climate Control", data=user_input)

        # Show the form to input the Modbus configuration
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("port", default="/dev/ttyUSB0"): str,  # Modbus serial port
                vol.Required("baudrate", default=19200): int,
                vol.Required("parity", default="E"): vol.In(["N", "E", "O"]),  # Parity
                vol.Required("stopbits", default=1): vol.Coerce(int),
                vol.Required("slave", default=30): int,
            })
        )
