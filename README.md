# Nilan Climate Control Integration for Home Assistant

This project provides a custom integration to control the Nilan Climate System using Home Assistant. It enables setting air exchange modes, hot water setpoints, fan modes, and much more using a Modbus client connection.

Important! The code only support Nilan Compact P Nordic. Please contact me if you want dispose of any other Nilan units with Modbus support. Also note that Modbus over ethernet is not supported.

## Features
- Monitor and control HVAC modes (Heat, Cool, Heat_Cool).
- Set target temperatures for heating/cooling.
- Adjust fan modes with different speed settings.
- Set air exchange modes (Energy, Comfort, ComfortWater).
- Configure hot water setpoints for the boiler system.
- Access various Nilan system metrics like humidity, fan speeds, and alarm statuses.

## Prerequisites
- **Home Assistant**: Make sure Home Assistant is properly installed.
- **Nilan Climate System**: This integration is designed for use with a Nilan Climate Control device.
- **Modbus Client**: Ensure that the Nilan device is accessible over Modbus.

## Installation
1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   ```

2. **Copy the Integration**:
   - Copy the `custom_components/nilan` directory into your Home Assistant configuration folder (`<config_dir>/custom_components/nilan`).

3. **Add Configuration**:
   - Update your `configuration.yaml` with the following:
     ```yaml
     nilan:
       modbus_client: <modbus_client_connection>
       slave: <slave_id>
     ```

4. **Restart Home Assistant**.

## Configuration
- **Air Exchange Mode**: Set using the `set_air_exchange_mode` service.
  - Available modes: `Energy`, `Comfort`, `ComfortWater`.
- **Hot Water Setpoints**: Set using the `set_hotwater_setpoints` service.
  - Specify `top_temperature` and/or `bottom_temperature` values (in °C).

## Usage
The integration exposes the following entity and services:

- **Entity**: `climate.nilan_climate_control`
  - Monitors and controls Nilan HVAC.

- **Services**:
  - `nilan.set_air_exchange_mode`: Set the air exchange mode.
  - `nilan.set_hotwater_setpoints`: Configure the hot water setpoints.

### Example Script for Setting Air Exchange Mode
```yaml
service: nilan.set_air_exchange_mode
target:
  entity_id: climate.nilan_climate_control
data:
  mode: "ComfortWater"
```

### Example Script for Setting Hot Water Setpoints
```yaml
service: nilan.set_hotwater_setpoints
target:
  entity_id: climate.nilan_climate_control
data:
  top_temperature: 50
  bottom_temperature: 45
```

## Troubleshooting
- Ensure the **Modbus client** connection is correctly set up and accessible.
- Make sure you use the **correct entity ID** (`climate.nilan_climate_control`) when calling services.
- Verify configuration changes using **Home Assistant Developer Tools** (States and Logs).

## Development
- **Voluptuous** is used for schema validation.
- **ModbusException** errors are logged for troubleshooting communication issues.
- Service registration uses `platform.async_register_entity_service` for entity-level actions.

## Contributing
Feel free to open issues, fork, or submit pull requests. Contributions are welcome!

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments
- **Home Assistant Documentation**: Provided guidance on custom components and service registration.
- **Nilan**: For the HVAC system and device documentation.

