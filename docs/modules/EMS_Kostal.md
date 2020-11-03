# Kostal EMS Module

## Introduction

The Kostal EMS Module allows energy generation (solar) to be fetched via ModBus TCP, which is a available with all modern Kostal inverters.

The module supports fetching generation and consumption values directly via ```ModBus TCP``` protocol.

## Configuration

The following table shows the available configuration parameters for the SolarEdge EMS Module:

| **Parameter** | **Value** |
| ------------- | --------- |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will query values via ModBus TCP |
| serverIP      | *required* The IP address of the Kostal inverter in the same LAN (usally something link 192.168.1.x). |
| modbusPort    | *required* The port of the ModBus server in the Kostal inverter. The default value (1502) will work in most cases. |
| unitID        | *required* The unit ID of the Kostal inverter in the ModBus. Default value is 71 which should work in most cases. |

Please note, if any of the required parameters for the Kostal EMS module are not specified in the module configuration, the module will not work and unload at start time!

## JSON Configuration Example

```
"Kostal": {
  "enabled": true,
  "serverIP": "192.168.1.100",
  "modbusPort": 1502,
  "unitID": 71
}
```


## Contact
If you have problems with this module, I can provide limited support via hopfi2k@me.com 