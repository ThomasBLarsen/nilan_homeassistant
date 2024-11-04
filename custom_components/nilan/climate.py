import logging
import voluptuous as vol
from homeassistant.components.logbook import async_log_entry
from pymodbus.exceptions import ModbusException
from homeassistant.components.climate import ClimateEntity
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define service constants and schemas
SERVICE_SET_AIR_EXCHANGE_MODE = "set_air_exchange_mode"
SERVICE_SET_HOTWATER_SETPOINTS = "set_hotwater_setpoints"

SET_AIR_EXCHANGE_MODE_SCHEMA = cv.make_entity_service_schema({
    vol.Required("mode"): vol.In(["Energy", "Comfort", "ComfortWater"]),
})

SET_HOTWATER_SETPOINTS_SCHEMA = cv.make_entity_service_schema({
    vol.Optional("top_temperature"): vol.Coerce(float),
    vol.Optional("bottom_temperature"): vol.Coerce(float),
})

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up Nilan climate platform from a config entry."""
    climate_entity = NilanClimateEntity(hass)
    async_add_entities([climate_entity], update_before_add=True)

    # Register service for setting air exchange mode as a domain service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AIR_EXCHANGE_MODE,
        climate_entity.async_handle_set_air_exchange_mode,
        schema=SET_AIR_EXCHANGE_MODE_SCHEMA,
    )

    # Register service for setting hot water setpoints as a domain service
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HOTWATER_SETPOINTS,
        climate_entity.async_handle_set_hotwater_setpoints,
        schema=SET_HOTWATER_SETPOINTS_SCHEMA,
    )
class NilanClimateEntity(ClimateEntity):
    """Representation of a Nilan Climate control."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the climate entity."""
        self.hass = hass
        self.client = hass.data.get(DOMAIN).get("modbus_client")
        self._slave = hass.data.get(DOMAIN).get("slave")
        self._attr_unique_id = "nilan_climate_control"
        self.target_temperature_step = 1.0
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        )
        self.target_temperature = None
        self.current_temperature = None
        self.current_humidity = None
        self.requested_capacity = None
        self.actual_capacity = None
        self.inlet_fan_speed = None
        self.exhaust_fan_speed = None
        self.days_since_filter_change = None
        self.days_to_filter_change = None
        self.alarm_status = None
        self.ventilation_state = None
        self.air_exch_mode = None
        self.top_temperature_setpoint = None
        self.bottom_temperature_setpoint = None
        self.cooling_setpoint = None
        self.sensor_values = {}
        self._attr_fan_mode = None
        self._attr_fan_modes = ["off", "min", "normal-low", "normal-high", "high"]
        self._slave = 30
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
        self._attr_hvac_mode = None
        self._hvac_action = HVACAction.OFF
        _LOGGER.info("Nilan Climate Control initialized")

    async def async_added_to_hass(self):
        """Run when the entity is added to Home Assistant."""
        if not self.client:
            _LOGGER.error("Modbus client not found.")
            return

        try:
            await self._read_hotwater_setpoints()
        except Exception as e:
            _LOGGER.error(f"Failed to read hot water setpoints: {e}")

    @property
    def name(self):
        """Return the name of the device."""
        return "Nilan Climate Control"

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = {
            "current_humidity": self.current_humidity,
            "target_temperature": self.target_temperature,
            "current_temperature": self.current_temperature,
            "fan_mode": self._attr_fan_mode,
            "hvac_mode": self._attr_hvac_mode,
            "hvac_action": self._hvac_action,
            "requested_capacity": self.requested_capacity,
            "actual_capacity": self.actual_capacity,
            "inlet_fan_speed": self.inlet_fan_speed,
            "exhaust_fan_speed": self.exhaust_fan_speed,
            "days_since_filter_change": self.days_since_filter_change,
            "days_to_filter_change": self.days_to_filter_change,
            "alarm_status": self.alarm_status,
            "ventilation_state": self.ventilation_state,
            "air exchange mode": self.map_air_exch_mode(self.air_exch_mode),
            "Boiler top temperature setpoint": self.top_temperature_setpoint,
            "Boiler bottom temperature setpoint": self.bottom_temperature_setpoint,
            "cooling_setpoint": self.map_cooling_setpoint(self.cooling_setpoint),
        }
        attributes.update(self.sensor_values)
        return attributes

    async def async_update(self):
        """Fetch new state data for the sensor."""
        if self.client is None:
            _LOGGER.error("Modbus client not found.")
            return

        try:
            await self._read_hvac_mode()
            await self._read_hvac_action()
            await self._read_temperature_humidity()
            await self._read_fan_speeds()
            await self._read_capacities()
            await self._read_filter_data()
            await self._read_alarm_status()
            await self._read_ventilation_state()
            await self._read_sensor_values()
            await self._read_hotwater_setpoints()
            await self._read_cooling_setpoint()
            await self._read_air_exchange_mode()
            await self.async_get_fan_mode()
            await self.async_log_hvac_status()
        except ModbusException as e:
            _LOGGER.error("Error communicating with Nilan device: %s", e)

    async def _read_hvac_mode(self):
        """Read HVAC mode."""
        result = await self.client.read_holding_registers(1002, count=1, slave=self._slave)
        if not result.isError() and result.registers:
            hvac_mode = {
                1: HVACMode.HEAT,
                2: HVACMode.COOL,
                3: HVACMode.HEAT_COOL,
            }.get(result.registers[0], HVACMode.OFF)  # Default to HVACMode.OFF if value is unknown
            self._attr_hvac_mode = hvac_mode
            _LOGGER.info(f"HVAC mode: {hvac_mode}")
        else:
            _LOGGER.warning("Unexpected value or error in reading HVAC mode")

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target HVAC mode."""
        try:
            register_value = {
                HVACMode.HEAT: 1,
                HVACMode.COOL: 2,
                HVACMode.HEAT_COOL: 3,
            }.get(hvac_mode, 0)  # Default to 0 if the hvac_mode is not recognized

            result = await self.client.write_registers(1002, [register_value], slave=self._slave)
            if not result.isError():
                self._attr_hvac_mode = hvac_mode
                self.schedule_update_ha_state()
                _LOGGER.info(f"HVAC mode set to {hvac_mode}")
            else:
                _LOGGER.warning("Failed to set HVAC mode.")
        except ModbusException as e:
            _LOGGER.error("Error setting HVAC mode: %s", e)

    async def _read_hvac_action(self):
        """Read and update the HVAC action."""
        result = await self.client.read_input_registers(1002, count=1, slave=self._slave)
        if not result.isError():
            hvac_action_value = result.registers[0]
            new_hvac_action = self.map_hvac_action(hvac_action_value)
            if new_hvac_action != self._hvac_action:
                self._hvac_action = new_hvac_action
                if self._hvac_action is not None:
                    async_log_entry(self.hass, "Nilan Climate Control", f"HVAC action changed to {self._hvac_action}")
                _LOGGER.info(f"HVAC action: {self._hvac_action}")
        else:
            _LOGGER.error("Error reading Nilan HVAC action")

    def map_hvac_action(self, value):
        """Map the HVAC action value from the control state."""
        hvac_action_map = {
            0: HVACAction.OFF,
            1: "Shifting",
            2: "Stopping",
            3: "Start",
            4: "Standby",
            5: "Ventilation stop",
            6: HVACAction.FAN,
            7: HVACAction.HEATING,
            8: HVACAction.COOLING,
            9: "Hotwater",
            10: "Legionella",
            11: "Cooling and Hotwater",
            12: "Central heating",
            13: "Defrost",
            14: "Frost secure",
            15: "Dervice",
            16: "Alarm",
            17: "Heating hotwater",
        }
        return hvac_action_map.get(value, HVACAction.OFF)

    async def _read_temperature_humidity(self):
        """Read temperature and humidity related values."""
        # Get set temperature
        result = await self.client.read_holding_registers(1004, count=1, slave=self._slave)
        if not result.isError():
            self.target_temperature = result.registers[0] * 0.01
            _LOGGER.info(f"Target temperature: {self.target_temperature} °C")

        # Get actual temperature
        result = await self.client.read_input_registers(1202, count=1, slave=self._slave)
        if not result.isError():
            self.current_temperature = result.registers[0] * 0.01
            _LOGGER.info(f"Current temperature: {self.current_temperature} °C")

        # Get actual humidity
        result = await self.client.read_input_registers(221, count=1, slave=self._slave)
        if not result.isError():
            self.current_humidity = result.registers[0] * 0.01
            _LOGGER.info(f"Current humidity: {self.current_humidity} %")

    async def _read_fan_speeds(self):
        """Read fan speed related values."""
        # Get inlet fan speed
        result = await self.client.read_input_registers(1101, count=1, slave=self._slave)
        if not result.isError():
            self.inlet_fan_speed = result.registers[0]
            _LOGGER.info(f"Inlet fan speed: {self.inlet_fan_speed}")

        # Get exhaust fan speed
        result = await self.client.read_input_registers(1102, count=1, slave=self._slave)
        if not result.isError():
            self.exhaust_fan_speed = result.registers[0]
            _LOGGER.info(f"Exhaust fan speed: {self.exhaust_fan_speed}")

    async def _read_capacities(self):
        """Read capacity related values."""
        # Get requested capacity
        result = await self.client.read_input_registers(1205, count=1, slave=self._slave)
        if not result.isError():
            self.requested_capacity = result.registers[0] * 0.01
            _LOGGER.info(f"Requested capacity: {self.requested_capacity}")

        # Get actual capacity
        result = await self.client.read_input_registers(1206, count=1, slave=self._slave)
        if not result.isError():
            self.actual_capacity = result.registers[0] * 0.01
            _LOGGER.info(f"Actual capacity: {self.actual_capacity}")

    async def _read_filter_data(self):
        """Read filter related data."""
        # Get days since last filter change
        result = await self.client.read_input_registers(1103, count=1, slave=self._slave)
        if not result.isError():
            self.days_since_filter_change = result.registers[0]
            _LOGGER.info(f"Days since filter change: {self.days_since_filter_change}")

        # Get days to next filter change
        result = await self.client.read_input_registers(1104, count=1, slave=self._slave)
        if not result.isError():
            self.days_to_filter_change = result.registers[0]
            _LOGGER.info(f"Days to next filter change: {self.days_to_filter_change}")

    async def _read_alarm_status(self):
        """Read alarm status."""
        result = await self.client.read_input_registers(400, count=1, slave=self._slave)
        if not result.isError():
            new_alarm_status = result.registers[0]
            if new_alarm_status != self.alarm_status:
                self.alarm_status = new_alarm_status
                async_log_entry(self.hass, "Nilan Climate Control", f"Alarm status changed to {self.alarm_status}")
                _LOGGER.info(f"Alarm status: {self.alarm_status}")
        else:
            _LOGGER.error("Error reading alarm status")

    async def _read_ventilation_state(self):
        """Read ventilation state."""
        result = await self.client.read_input_registers(3102, count=1, slave=self._slave)
        if not result.isError():
            self.ventilation_state = result.registers[0]
            _LOGGER.info(f"Ventilation state: {self.ventilation_state}")

    async def _read_sensor_values(self):
        """Read additional sensor values."""
        sensors = {
            "intake_temperature": [201, 0.01],
            "room_exhaust_temperature": [204, 0.01],
            "hot_water_top_temperature": [211, 0.01],
            "hot_water_bottom_temperature": [212, 0.01],
            "hot_water_anode": [216, 0.01],
        }
        for sensor, params in sensors.items():
            result = await self.client.read_input_registers(params[0], count=1, slave=self._slave)
            if not result.isError():
                self.sensor_values[sensor] = result.registers[0] * params[1]
                _LOGGER.info(f"{sensor.replace('_', ' ').title()}: {self.sensor_values[sensor]}")

    async def _read_air_exchange_mode(self):
        """Read air exchange mode."""
        result = await self.client.read_holding_registers(1100, count=1, slave=self._slave)
        if not result.isError():
            self.air_exch_mode = result.registers[0]
            _LOGGER.info(f"Air exchange mode: {self.map_air_exch_mode(self.air_exch_mode)}")

    async def async_set_air_exchange_mode(self, mode):
        """Set air exchange mode."""
        try:
            # Convert the mode to the corresponding register value
            mode_value = {
                "Energy": 0,
                "Comfort": 1,
                "ComfortWater": 2  # Corrected here
            }.get(mode)

            if mode_value is not None:
                result = await self.client.write_registers(1100, [mode_value], slave=self._slave)
                if not result.isError():
                    self.air_exch_mode = mode_value
                    self.schedule_update_ha_state()
                    _LOGGER.info(f"Air exchange mode set to {mode}")
                else:
                    _LOGGER.warning("Failed to set air exchange mode.")
            else:
                _LOGGER.error(f"Invalid air exchange mode: {mode}")
        except ModbusException as e:
            _LOGGER.error("Error setting air exchange mode: %s", e)

    def map_air_exch_mode(self, value):
        """Map air exchange mode values."""
        air_exch_map = {
            0: "Energy",
            1: "Comfort",
            2: "ComfortWater",
        }
        return air_exch_map.get(value, "Unknown")

    async def _read_cooling_setpoint(self):
        """Read cooling setpoint."""
        result = await self.client.read_holding_registers(1200, count=1, slave=self._slave)
        if not result.isError():
            self.cooling_setpoint = result.registers[0]
            _LOGGER.info(f"Cooling setpoint: {self.cooling_setpoint} ({self.map_cooling_setpoint(self.cooling_setpoint)})")

    async def async_set_cooling_setpoint(self, setpoint):
        """Set cooling temperature setpoint."""
        try:
            result = await self.client.write_registers(1200, [setpoint], slave=self._slave)
            if not result.isError():
                self.cooling_setpoint = setpoint
                self.schedule_update_ha_state()
                _LOGGER.info(f"Cooling setpoint set to {self.map_cooling_setpoint(setpoint)}")
        except ModbusException as e:
            _LOGGER.error("Error setting cooling setpoint: %s", e)

    def map_cooling_setpoint(self, value):
        """Map cooling setpoint values."""
        cooling_set_map = {
            0: "Off",
            1: "Set + 0 °C",
            2: "Set + 1 °C",
            3: "Set + 2 °C",
            4: "Set + 3 °C",
            5: "Set + 4 °C",
            6: "Set + 5 °C",
            7: "Set + 7 °C",
            8: "Set + 10 °C",
        }
        return cooling_set_map.get(value, "Unknown")

    async def _read_hotwater_setpoints(self):
        """Read hot water setpoints from the Nilan device."""
        if not self.client:
            _LOGGER.error("Modbus client not initialized.")
            return

        result = await self.client.read_holding_registers(1700, count=1, slave=self._slave)
        if result.isError():
            _LOGGER.error("Failed to read top boiler temperature.")
        else:
            self.top_temperature_setpoint = result.registers[0] * 0.01
            _LOGGER.info(f"Top boiler temperature setpoint: {self.top_temperature_setpoint} °C")

        result = await self.client.read_holding_registers(1701, count=1, slave=self._slave)
        if result.isError():
            _LOGGER.error("Failed to read bottom boiler temperature.")
        else:
            self.bottom_temperature_setpoint = result.registers[0] * 0.01
            _LOGGER.info(f"Bottom boiler temperature setpoint: {self.bottom_temperature_setpoint} °C")

    async def async_set_hotwater_setpoints(self, top_temperature=None, bottom_temperature=None):
        """Set hot water setpoints for the boiler."""
        try:
            if top_temperature is not None:
                top_value = int(top_temperature * 100)  # Convert to Modbus format
                result = await self.client.write_registers(1700, [top_value], slave=self._slave)
                if not result.isError():
                    self.top_temperature_setpoint = top_temperature
                    _LOGGER.info(f"Boiler top temperature setpoint set to {top_temperature} °C")
                else:
                    _LOGGER.warning("Failed to set Boiler top temperature setpoint.")

            if bottom_temperature is not None:
                bottom_value = int(bottom_temperature * 100)  # Convert to Modbus format
                result = await self.client.write_registers(1701, [bottom_value], slave=self._slave)
                if not result.isError():
                    self.bottom_temperature_setpoint = bottom_temperature
                    _LOGGER.info(f"Boiler bottom temperature setpoint set to {bottom_temperature} °C")
                else:
                    _LOGGER.warning("Failed to set Boiler bottom temperature setpoint.")

            self.schedule_update_ha_state()

        except ModbusException as e:
            _LOGGER.error("Error setting hot water setpoints: %s", e)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.error("No temperature provided to set_temperature")
            return
        try:
            register_value = int(temperature / 0.01)
            result = await self.client.write_registers(1004, [register_value], slave=self._slave)
            if not result.isError():
                self.target_temperature = temperature
                self.schedule_update_ha_state()
        except ModbusException as e:
            _LOGGER.error("Error communicating with Nilan device: %s", e)

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        try:
            register_value = {
                "off": 0,
                "min": 1,
                "normal-low": 2,
                "normal-high": 3,
                "high": 4,
            }.get(fan_mode)

            if register_value is not None:
                result = await self.client.write_registers(1003, [register_value], slave=self._slave)
                if not result.isError():
                    self._attr_fan_mode = fan_mode
                    self.schedule_update_ha_state()
                    _LOGGER.info(f"Fan mode set to {fan_mode}")
            else:
                _LOGGER.error(f"Invalid fan mode: {fan_mode}")
        except ModbusException as e:
            _LOGGER.error("Error setting fan mode: %s", e)

    async def async_get_fan_mode(self):
        """Read and update the fan mode."""
        result = await self.client.read_holding_registers(1003, count=1, slave=self._slave)
        if not result.isError():
            fan_mode_value = result.registers[0]
            new_fan_mode = {
                0: "off",
                1: "min",
                2: "normal-low",
                3: "normal-high",
                4: "high",
            }.get(fan_mode_value)
            if new_fan_mode != self._attr_fan_mode:
                self._attr_fan_mode = new_fan_mode
                _LOGGER.info(f"Fan mode updated to: {self._attr_fan_mode}")
        else:
            _LOGGER.error("Error reading fan mode")

    async def async_log_hvac_status(self):
        """Log the status of the HVAC system and hot water temperatures."""
        _LOGGER.info(f"HVAC Mode: {self._attr_hvac_mode}, HVAC Action: {self._hvac_action}")
        _LOGGER.info(f"Top Hot Water Temperature: {self.top_temperature_setpoint} °C, Bottom Hot Water Temperature: {self.bottom_temperature_setpoint} °C")

    async def async_handle_set_air_exchange_mode(self, call: ServiceCall):
        """Handle the service call to set air exchange mode."""
        mode = call.data.get("mode")
        if mode in ["Energy", "Comfort", "ComfortWater"]:
            await self.async_set_air_exchange_mode(mode)
        else:
            _LOGGER.error(f"Invalid air exchange mode provided: {mode}")

    async def async_handle_set_hotwater_setpoints(self, call):
        """Handle the service call to set hot water setpoints."""
        top_temperature = call.data.get("top_temperature")
        bottom_temperature = call.data.get("bottom_temperature")

        if top_temperature is not None or bottom_temperature is not None:
            await self.async_set_hotwater_setpoints(
                top_temperature=top_temperature, bottom_temperature=bottom_temperature
            )
        else:
            _LOGGER.error("Invalid temperatures provided for hot water setpoints")
