# Open Energy Monitor EMS Module

## Introduction

The Open Energy Monitor (EmonCMS) EMS module allows fetching of solar generation and consumption values from Open Energy Monitor. This is useful as it allows a general interface to data which may be combined within Open Energy Monitor, eg. accumulating generation data from multiple inverters.

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | EmonCMS                        |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, Tested            |

## Configuration

The following table shows the available configuration parameters for the HASS EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| apiKey      | *required* API Key. You can find this under "Feed API Help" in your Open Energy Monitor Feeds page. |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll HomeAssistant sensors. |
| consumptionFeed | *optional* The ID of the consumption feed in OpenEnergyMonitor. |
| generationFeed  | *optional* The ID of the generation feed in OpenEnergyMonitor. |
| serverIP    | *required* The IP address or hostname of the Open Energy Monitor instance. We will poll the REST HTTP API. |
| serverPort  | *optional* The port that the webserver for Open Energy Monitor is listening on. Defaults to 80 (HTTP). |
| serverPath  | *optional* The HTTP path, if Open Energy Monitor is setup in a subdirectory. Defaults to empty, you should add a trailing '/'. |
| useHttps    | *optional* Boolean value, ```true``` or ```false```. Should it use https instead of http. |

### JSON Configuration Example

```
"EmonCMS": {
  "apiKey": "ABC123",
  "enabled": true,
  "consumptionFeed": 1,
  "generationFeed": 2,
  "serverIP": "power.local",
  "serverPort": 80
}
```

