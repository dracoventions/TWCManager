# HomeAssistant Status Module

## Introduction

The HomeAssistant Status Module provides a mechanism to publish sensor states to HomeAssistant via the HomeAssistant API.

The module uses a long-term access key that is created through the HASS web interface, which allows the module to send updates to the sensors listed below without needing hard-coded credentials.

## HomeAssistant Sensors

The following sensors and their values are published to HomeAsssitant via the HomeAssistant HTTP API.

| HomeAssistant Sensor                     | Value                              | Example |
| ---------------------------------------- | ------------------------------------ | ----- |
| sensor.twcmanager_all_total_amps_in_use  | Float: Amps in use across all slaves | 16.24 |
| sensor.twcmanager_*charger*_amps_in_use  | Float: Amps in use for given Slave TWC | 8.52 |
| sensor.twcmanager_*charger*_amps_max     | Integer: Reported maximum amperage per Slave TWC | 32 |
| sensor.twcmanager_*charger*_cars_charging | Boolean: Will be 0 if Slave TWC does not have a connected charging vehicle, or 1 if it does. |
| sensor.twcmanager_*charger*_charger_load_w | Integer: Actual power being consumed as reported by the Slave TWC. | 2977 |
| sensor.twcmanager_*charger*_current_vehicle_vin | String: The VIN of a vehicle currently charging from this Slave TWC. |
| sensor.twcmanager_*charger*_last_vehicle_vin | String: The VIN of the vehicle previously charging from this Slave TWC. |
| sensor.twcmanager_*charger*_lifetime_kwh  | Integer: Lifetime kWh output by specified charger. | 159 |
| sensor.twcmanager_*charger*_power      | Float: Actual amps being consumed as reported by the Slave TWC. | 14.51 |
| sensor.twcmanager_*charger*_state      | Integer: State code reported by TWC. Please see table below for state codes. |
| sensor.twcmanager_*charger*&#x5f;voltage_phase&#x5f;*phase* | Integer: Volts per phase (a/b/c) per Slave TWC  | 243 |
| sensor.twcmanager_config_min_amps_per_twc | Integer: Minimum amps to charge per TWC (from config) | 6 |
| sensor.twcmanager_config_max_amps_for_slaves | Integer: Total number of amps on power circuit to divide amongst Slave TWCs | 32 |

### State Codes

The following state codes are reported by Slave TWCs:

| State Code | Description |
| ---------- | ----------- |
| 0          | Ready. Car may or may not be plugged in to TWC |
| 1          | Plugged in and charging                        |
| 2          | Error                                          |
| 3          | Plugged in, do not charge (vehicle finished charging or error) |
| 4          | Plugged in, ready to charge or charge is scheduled |
| 5          | Busy                                               |
| 6          | TBA. Version 2 only.  |
| 7          | TBA. Version 2 only.  |
| 8          | Starting to charge.                                |
| 9          | TBA. Version 2 only.  |
| 10         | Amp adjustment period complete. |
| 15         | Unknown.              |
