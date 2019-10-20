# The Energy Detective EMS Module

## Introduction

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | TED                            |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Generation                     |
| **Status**      | Implemented, *untested*        |

## Configuration

The following table shows the available configuration parameters for the TED EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll TED. |
| serverIP    | *required* The IP address of the TED device. We will poll this device's API. |
| serverPort  | *optional* TED Web Server port. This is the port that we should connect to. |

### JSON Configuration Example

```
"TED": {
  "enabled": true,
  "serverIP": "192.168.1.1",
  "serverPort": 80
}
```
