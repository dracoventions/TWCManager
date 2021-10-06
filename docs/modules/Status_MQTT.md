# MQTT Status Module

## Introduction

The MQTT Status Module provides a mechanism to publish MQTT topic values to an MQTT broker.

The module uses supplied credentials to connect to the MQTT server, and publishes status updates. The name of the MQTT topics used are prefixed with a specified prefix, which is configured as TWC by default in the configuration file.

## MQTT Topics

| MQTT Topic                       | Value                                  | Example |
| -------------------------------- | -------------------------------------- | ------- |
| *prefix*/all/totalAmpsInUse      | Float: Amps in use across all slaves   | 16.24 |
| *prefix*/*charger*/ampsInUse     | Float: Amps in use for given Slave TWC | 8.52 |
| *prefix*/*charger*/ampsMax       | Integer: Reported maximum amperage per Slave TWC | 32 |
| *prefix*/*charger*/carsCharging  | Boolean: Will be 0 if Slave TWC does not have a connected charging vehicle, or 1 if it does. |
| *prefix*/*charger*/currentVehicleVIN | String: The VIN of a vehicle currently charging from this Slave TWC. |
| *prefix*/*charger*/lastVehicleVIN | String: The VIN of the vehicle previously charging from this Slave TWC. |
| *prefix*/*charger*/lifetimekWh   | Integer: Lifetime kWh output by specified charger. | 159 |
| *prefix*/*charger*/power         | Float: Actual amps being consumed as reported by the Slave TWC. | 14.51 |
| *prefix*/*charger*/state         | Integer: State code reported by TWC. Please see table below for state codes. |
| *prefix*/*charger*/voltagePhase*X* | Integer: Volts per phase (a/b/c) per Slave TWC  | 243 |
| *prefix*/config/maxAmpsForSlaves | Integer: Total number of amps on power circuit to divide amongst Slave TWCs | 32 |
| *prefix*/config/minAmpsPerTWC    | Integer: Minimum amps to charge per TWC (from config) | 6 |

### Rate limiting

By default, the MQTT Status Module will limit one update per topic per 60 seconds. The reason for this is that MQTT publishing is an asynchronous process. Updates are queued and sent in order to the MQTT broker. If there was a delay in publishing and acknowledging the MQTT messages on the broker side, the queue would continue to grow and the message buffer would consume more memory until it eventually ran out of available memory.

This isn't going to be an issue in all environments, but defaulting to a configuration that cannot effectively handle latency would be a worse situation. If you'd like to reduce or even disable the rate limiting, you can adjust it in the configuration file:

```
"status": {
  "MQTT": {
    "ratelimit": {number in seconds for how many seconds per update per topic, or 0 to disable)
  }
}
```

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

