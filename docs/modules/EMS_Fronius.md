# Fronius Inverter EMS Module

## Introduction

Fronius Inverters provide a solar.web interface locally on the inverter itself, which allows querying of Solar Generation information. If you have a Fronius Meter installed, the solar.web interface also provides Consumption information.

Fronius Inverters connect via wifi. The serverIP IP address is the IP that the Fronius Inverter is provided via DHCP after connecting to the Wifi network.

### Note

In many Fronius installations, the installation will involve a Fronius Meter mounted within the electricity meter box. If you have one of these installed, it will be between 2-4 DIN slots wide, with an LCD screen showing metering information, and will have a model number similar to 63A-1 or 63A-3.

If you have such a meter installed, you are able to obtain Consumption information via the Fronius interface, and it is likely that the TWC's power draw is being metered. If this is the case, the TWC's load will show as Consumption via the Fronius EMS module. If this is the case, please ensure the following configuration setting is enabled in your ```config.json``` file:

```
{
    "config": {
        "subtractChargerLoad": true
    }
}
```

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | Fronius                        |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, Mature, Tested    |

## Configuration

The following table shows the available configuration parameters for the Fronius EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the Fronius Inverter. |
| serverIP    | *required* The IP address of the Fronius Inverter. We will poll this device's HTTP API. |
| serverPort  | *optional* Web Server port. This is the port that we should connect to. This is almost always 80 (HTTP). |

### JSON Configuration Example

```
"Fronius": {
  "enabled": true,
  "serverIP": "192.168.1.2",
  "serverPort": 80
}
```
