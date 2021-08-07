# HTTP Control Module

## Introduction

The HTTP Control module allows control of the TWCManager Tesla Wall Charger controller via an in-built HTTP web server.

The web-server is multi-threaded (ie, it can be managed by multiple clients simultaneously), but does not support HTTPS encryption. It listens on Port 8080. As of release v1.1.5, it does not currently have any configurable options (but will in the future).

### HTTP Control Module vs IPC Web Interface

There are two separate interfaces for managing TWCManager via web browser. These are:

   * WebIPC - The original web interface bundled with TWCManager
   * HTTPControl - The new in-built web interface
   
**Benefits of HTTPControl**

   * Tightly integrated with the TWCManager controller. Less development lead-time to add functions.

**Drawbacks of HTTPControl**

   * Does not support HTTPS encryption.

### Status

| Detail          | Value          |
| --------------- | -------------- |
| **Module Name** | HTTPControl    |
| **Module Type** | Status         |
| **Status**      | In Development |

## Configuration

The following table shows the available configuration parameters for the MQTT Control module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will enable HTTP control. |
| listenPort | *optional* HTTP Web Server port. Defaults to port 8080. |

### JSON Configuration Example

```
"control": {
  "HTTP": {
    "enabled": true,
    "listenPort": 8080
  }
}
```

## Using the HTTP Web Interface

If you have enabled HTTPControl, access it via the specified port. For example if your TWCManager machine is 192.168.1.1 and listenPort is 8080, access the HTTP interface with the following URL:

<a href="http://192.168.1.1:8080/">http://192.168.1.1:8080/</a>

## Using the API Interface

The HTTPControl web server provides an API interface under the /api URL root. The following methods are used when interacting with the API interface:

   * GET requests for requesting information or parameters
   * POST requests for performing actions or providing data

The following API endpoints exist:

| Endpoint                    | Method | Description                                       |
| --------------------------- | ------ | ------------------------------------------------- |
| [addConsumptionOffset](control_HTTP_API/addConsumptionOffset.md) | POST | Add or Edit a Consumption Offset value | 
| [cancelChargeNow](control_HTTP_API/cancelChargeNow.md) | POST | Cancels active chargeNow configuration        |
| [chargeNow](control_HTTP_API/chargeNow.md)             | POST  | Instructs charger to start charging at specified rate |
| [deleteConsumptionOffset](control_HTTP_API/deleteConsumptionOffset.md) | POST | Delete a Consumption Offset value |
| getConfig                | GET    | Provides the current configuration                |
| [getConsumptionOffsets](control_HTTP_API/getConsumptionOffsets.md) | GET | List configured offsets               |
| getPolicy                | GET  | Provides the policy configuration                 |
| getSlaveTWCs             | GET  | Provides a list of connected Slave TWCs and their state |
| getStatus                | GET  | Provides the current status (Charge Rate, Policy) |
| getUUID                  | GET  | Provides a unique ID for this particular master, based on the physical MAC address |
| [saveSettings](control_HTTP_API/saveSettings.md)         | POST | Saves settings to settings file |
| [sendStartCommand](control_HTTP_API/sendStartCommand.md) | POST | Sends the Start command to all Slave TWCs    |
| setSetting               | POST | Set settings |
| [sendStopCommand](control_HTTP_API/sendStopCommand.md)   | POST | Sends the Stop command to all Slave TWCs     |
| [setScheduledChargingSettings](control_HTTP_API/setScheduledChargingSettings.md)  | POST | Saves Scheduled Charging settings --> can be retrieved with getStatus |
