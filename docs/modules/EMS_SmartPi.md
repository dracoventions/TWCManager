# SmartPi EMS Module

This module allows querying of [SmartPi](https://www.enerserve.eu/en/smartpi.html) power sensors.

Note: Only Generation values are supported by this module. The power measured by the sensor will be evaluated as Generation if the value is Negative, or Consumption if the value is Positive and ```showConsumption``` is enabled, otherwise zero.. As a result, only a Generation or Consumption value should be shown at any time, but never both.

## Introduction

| **Parameter** | **Value** |
| ------------- | --------- |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the SmartPi Device |
| serverIP      | *required* The IP Address of the SmartPi Device |
| serverPort    | *required* The Port on which the SmartPi API is reachable |
| showConsumption | *optional* Determines whether we should show a negative Generation figure as zero (False, default), or as a positive Consumption figure (True). Note that this should not be enabled if you're using ```subtractChargerLoad``` in your ```config.json```. |

## JSON Configuration Example

The following configuration should be placed under the "sources" section of the config.json file in your installation, and will enable SmartPi EMS polling.

```
"SmartPi": {
  "enabled": true,
  "serverIP": "192.168.1.2",
  "serverPort": "1080"
}
```
