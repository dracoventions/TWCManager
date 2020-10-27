# SolarLog EMS Module

## Introduction

The SolarLog EMS Module allows energy generation and production to be fetched from the Solar-Log Base API (```https://www.solar-log.com/de/produkte-komponenten/solar-logTM-hardware/solar-log-base/```) that generates a webservice directly on the device

## Configuration

The following table shows the available configuration parameters for the SolarLog EMS Module:

| **Parameter** | **Value** |
| ------------- | --------- |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the SolarLog API |
| serverIP      | *required* The IP Address of the Solar-Log Base device. |
| excludeConsumptionInverters        | *optional and experimental* Indices of reading devices - to exclude consumption from. Needed if e.g. a boiler only heats with solar overhead - and you want to override this one. (it works for me - but there are perhaps some other use cases) |

Please note, if any of the required parameters for the SolarLog EMS module are not specified in the module configuration, the module will unload at start time.

## JSON Configuration Example

```
"SolarLog": {
  "enabled": false,
  "serverIP": "192.168.1.2",
  "excludeConsumptionInverters": [2, 3]
}, 
```

