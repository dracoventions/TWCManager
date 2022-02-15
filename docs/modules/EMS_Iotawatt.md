# IoTaWatt EMS Module

## Introduction

The IoTaWatt EMS module allows fetching of solar Generation and Consumption values from Iotawatt outputs.

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | Iotawatt                       |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Available            |

## Configuration

The following table shows the available configuration parameters for the IoTaWatt EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the IoTaWatt REST API. |
| outputConsumption | *optional* Name of Consumption output. |
| outputGeneration  | *optional* Name of Generation output. |
| serverIP    | *required* The IP address of the Iotawatt instance. |

### JSON Configuration Example

```
"Iotawatt": {
  "enabled": true,
  "outputConsumption": "Total_Consumption",
  "outputGeneration": "Solar",
  "serverIP": "192.168.1.2"
}
```

### Output Names

For IoTaWatt, the two outputs must be customized to point to the specific names you use within IoTaWatt. There is no default or common value for this, so it will require customization to work correctly. Note that only outputs (not inputs) can be used for this.

If you do not track one of these values (generation or consumption) via IoTaWatt, leave the parameter blank, and it will not be retrieved.
