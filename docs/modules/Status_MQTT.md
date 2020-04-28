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
| *prefix*/*charger*/power         | TBA |
| *prefix*/*charger*/state         | TBA |
| *prefix*/*charger*/voltagePhase*X* | Integer: Volts per phase (a/b/c) per Slave TWC  | 243 |
| *prefix*/config/maxAmpsForSlaves | TBA |
| *prefix*/config/minAmpsPerTWC    | TBA |
