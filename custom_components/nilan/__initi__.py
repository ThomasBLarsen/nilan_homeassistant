import logging
from homeassistant.core import HomeAssistant
from pymodbus.client import AsyncModbusSerialClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Nilan integration."""
    hass.data[DOMAIN] = {}

    return True

async def async_setup_entry(hass, entry):
    """Set up Nilan from a config entry."""
    config_data = entry.data

    # Create the Modbus client
    modbus_client = AsyncModbusSerialClient(
        method='rtu',
        port=config_data['port'],
        baudrate=config_data['baudrate'],
        parity=config_data['parity'],
        stopbits=config_data['stopbits'],
        timeout=3
    )

    # Attempt to connect the Modbus client
    connection = await modbus_client.connect()

    if connection:
        hass.data[DOMAIN]["modbus_client"] = modbus_client
        hass.data[DOMAIN]["slave"] = config_data['slave']
        _LOGGER.info("Modbus client successfully connected.")
    else:
        _LOGGER.error("Failed to connect Modbus client.")
        return False  # Return False if the client fails to connect

    # Set up the climate platform after Modbus client is ready
    await hass.config_entries.async_forward_entry_setups(entry, ["climate"])
    return True

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "climate")
