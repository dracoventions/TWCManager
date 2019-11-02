# Tesla Powerwall 2 EMS Module

## Introduction

The Tesla Powerwall 2 EMS module is used for fetching Solar Generation and Power Consumption values from a Tesla Powerwall 2 battery system.

The Tesla Powerwall 2 sits between a Solar generation system, the home electrical system and the electricity grid. This makes it very useful for monitoring the overall energy utilization of the house. Using this EMS module, we can calcuate how much solar power is being generated at any time, how much power consumption is currently metered, and we will then consume the difference between these values for the Tesla Wall Charger.

### Note

Given the location of the Powerwall in the home electrical system, it is highly likely that the TWC is drawing power from the Powerwall. As a result, the TWC's load will show as Consumption via the Powerwall's meter. If this is the case, please ensure the following configuration setting is enabled in your ```config.json``` file:

```
{
    "config": {
        "subtractChargerLoad": true
    }
}
```

### Status

| Detail          | Value                                         |
| --------------- | --------------------------------------------- |
| **Module Name** | Powerwall2                                    |
| **Module Type** | Energy Management System (EMS)                |
| **Features**    | Consumption, Generation, Grid Status, Voltage |
| **Status**      | Implemented, *untested*                       |

## Configuration

The following table shows the available configuration parameters for the Tesla Powerwall 2 EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the Tesla Powerwall 2. |
| password    | *optional* Password for the installer user, if required. If this is supplied, we will request a login token prior to API access. If not, requests will be performed without authentication. |
| serverIP    | *required* The IP address of the Powerwall2 device. We will poll this device's HTTPS API |
| serverPort  | *optional* API Server port. This is the port that we should connect to. This is almost always 443 (HTTPS) |

### JSON Configuration Example

```
"Powerwall2": {
  "enabled": true,
  "serverIP": "192.168.1.2",
  "serverPort": 443,
  "password": "test123"
}
```
