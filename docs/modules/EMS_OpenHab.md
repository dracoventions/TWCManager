# openHAB EMS Module

## Introduction

The openHAB EMS module allows fetching of solar Generation and Consumption values from openHAB items via the openHAB REST API.

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | OpenHab                        |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, *untested*        |

## Configuration

The following table shows the available configuration parameters for the openHAB EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, `true` or `false`. Determines whether we will poll openHAB items. |
| consumptionItem | *optional* Name of openHAB item displaying consumption. |
| generationItem  | *optional* Name of openHAB item displaying generation. |
| serverIP    | *required* The IP address of the openHAB instance. We will poll the REST HTTP API. |
| serverPort  | *optional* openHAB port. This is the port that we should connect to. Defaults to 8080. |

### JSON Configuration Example

```
"openHAB": {
  "enabled": true,
  "consumptionItem": "Solar_Consumption",
  "generationItem": "Solar_Generation",
  "serverIP": "192.168.1.2",
  "serverPort": "8080"
}
```

### Note

In case that the TWC's power draw is included in the value of your **consumptionItem**, please ensure the following configuration setting is enabled in your ```config.json``` file:

```
{
    "config": {
        "subtractChargerLoad": true
    }
}
```

### Item Names

The two settings "consumptionItem" and "generationItem" must be customized to point to the specific item names you use within openHAB. There is no default or common value for this, so it will require customization to work correctly.

If you do not track one of these values (generation or consumption) via openHAB, leave the parameter blank, and it will not be retrieved.

### Item Types

Make sure both items are of type *Number*. Using Number with a unit (*Number:\<dimension\>*) is also possible.

### openHAB .items File Example

```
// Just as a number
Number Solar_Generation "Generation [%d W]"
// As a number with unit
Number:Power Solar_Consumption "Consumption [%d W]"
```
