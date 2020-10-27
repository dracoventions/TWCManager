# HomeAssistant EMS Module

## Introduction

The HomeAssistant EMS module allows fetching of solar Generation and Consumption values from HomeAssistant sensors. This is useful as it allows a general interface to sensors which are implemented as dedicated HomeAssistant components. If there is no dedicated TWCManager module for an Energy Management System, using the HASS module allows the leveraging of HASS sensors.

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | HASS                           |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, Mature, Tested    |

## Configuration

The following table shows the available configuration parameters for the HASS EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| apiKey      | *required* API Key. |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll HomeAssistant sensors. |
| hassEntityConsumption | *optional* Name of HASS Consumption Sensor. |
| hassEntityGeneration  | *optional* Name of HASS Generation Sensor. |
| serverIP    | *required* The IP address of the HomeAssistant instance. We will poll the REST HTTP API. |
| serverPort  | *optional* HASS port. This is the port that we should connect to. Defaults to 8123 (HTTP). |
| useHttps    | *optional* Boolean value, ```true``` or ```false```. Should it the call use https instead of http. |

### JSON Configuration Example

```
"HASS": {
  "apiKey": "ABC123",
  "enabled": true,
  "hassEntityConsumption": "sensor.consumption",
  "hassEntityGeneration": "sensor.generation",
  "serverIP": "192.168.1.2",
  "serverPort": 8123
}
```

### Sensor Names

For HomeAssistant, the two settings below must be customized to point to the specific sensor names you use within HomeAssistant. There is no default or common value for this, so it will require customization to work correctly.

If you do not track one of these values (generation or consumption) via HASS, leave the parameter blank, and it will not be retrieved.

### API Key

We require a HomeAssistant API Key to provide privileges for access to HomeAssistant sensors.

To obtain a HASS API key, via browser, click on your user profile, and add a Long-Lived Access Token.
