# URL EMS Module

## Introduction

The URL EMS module allows fetching of solar Generation and Consumption values from URL items via HTTP(s).

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | URL                            |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, Tested            |

## Configuration

The following table shows the available configuration parameters for the URL EMS module.

| Parameter       | Value                                                                                                           |
| --------------- | --------------------------------------------------------------------------------------------------------------- |
| enabled         | *required* Boolean value, `true` or `false`. Determines whether we will poll URL items.                         |
| consumptionItem | *optional* Name of URL item displaying consumption.                                                             |
| generationItem  | *optional* Name of URL item displaying generation.                                                              |
| url             | *required* The base HTTP(s) URL of your serving instance. We will poll it combined with each item concatenated. |

### JSON Configuration Example

```
"URL": {
  "enabled": true,
  "url": "http://192.168.1.2/solar",
  "consumptionItem": "consumption",
  "generationItem": "generation"
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

The two settings "consumptionItem" and "generationItem" must be customized to point to the specific item names you use within URL. There is no default or common value for this, so it will require customization to work correctly.

If you do not track one of these values (generation or consumption) via URL, leave the parameter blank, and it will not be retrieved.

### Item Types

Make sure both items are of type *Number*. Using Number with a unit (*Number:\<dimension\>*) is also possible.

### URL .items Response Example

```
// Just as a number
Number Solar_Generation "Generation [%d W]"
// As a number with unit
Number:Power Solar_Consumption "Consumption [%d W]"
```

### Node-RED usage hints

You migh use this module to retrieve data provided via Node-RED. In this case your base URL could be https://noderedpath/solar. Item full URLs could be https://noderedpath/solar/consumption and https://noderedpath/solar/generation. This depends on your Node-RED installation.

Here is a sample flow for providing data from within your Node-RED instance:
```
[{"id":"aa674b85.b6fa28","type":"http in","z":"ec2c2ba0.1671a8","name":"https://noderedpath/solar/consumption","url":"/solar/consumption","method":"get","upload":false,"swaggerDoc":"","x":270,"y":860,"wires":[["936f9d51.3e518"]]},{"id":"936f9d51.3e518","type":"change","z":"ec2c2ba0.1671a8","name":"Set consumption","rules":[{"t":"set","p":"payload","pt":"msg","to":"consumption","tot":"flow"}],"action":"","property":"","from":"","to":"","reg":false,"x":530,"y":860,"wires":[["24574e64.4c0d12"]]},{"id":"a62985e.a00ef78","type":"http in","z":"ec2c2ba0.1671a8","name":"https://noderedpath/solar/generation","url":"/solar/generation","method":"get","upload":false,"swaggerDoc":"","x":260,"y":820,"wires":[["322cc66.4479c3a"]]},{"id":"24574e64.4c0d12","type":"http response","z":"ec2c2ba0.1671a8","name":"Response","statusCode":"","headers":{},"x":720,"y":820,"wires":[]},{"id":"322cc66.4479c3a","type":"change","z":"ec2c2ba0.1671a8","name":"Set generation","rules":[{"t":"set","p":"payload","pt":"msg","to":"generation","tot":"flow"}],"action":"","property":"","from":"","to":"","reg":false,"x":520,"y":820,"wires":[["24574e64.4c0d12"]]},{"id":"aa8b3d88.04ba1","type":"inject","z":"ec2c2ba0.1671a8","name":"Set generation to 5000W","props":[{"p":"payload"}],"repeat":"","crontab":"","once":false,"onceDelay":0.1,"topic":"","payload":"5000","payloadType":"num","x":250,"y":640,"wires":[["a8ae1926.caeba8"]]},{"id":"92052127.c97e2","type":"inject","z":"ec2c2ba0.1671a8","name":"Set generation to 1000W","props":[{"p":"payload"}],"repeat":"","crontab":"","once":false,"onceDelay":0.1,"topic":"","payload":"1000","payloadType":"num","x":250,"y":680,"wires":[["a8ae1926.caeba8"]]},{"id":"2540108e.a7f1","type":"inject","z":"ec2c2ba0.1671a8","name":"Set consumption to 300W","props":[{"p":"payload"}],"repeat":"","crontab":"","once":false,"onceDelay":0.1,"topic":"","payload":"300","payloadType":"num","x":250,"y":720,"wires":[["2af95a3.2b46fa6"]]},{"id":"c2cf49e3.f1aa78","type":"inject","z":"ec2c2ba0.1671a8","name":"Set consumption to 3500W","props":[{"p":"payload"}],"repeat":"","crontab":"","once":false,"onceDelay":0.1,"topic":"","payload":"3500","payloadType":"num","x":250,"y":760,"wires":[["2af95a3.2b46fa6"]]},{"id":"a8ae1926.caeba8","type":"change","z":"ec2c2ba0.1671a8","name":"Set generation","rules":[{"t":"set","p":"generation","pt":"flow","to":"payload","tot":"msg"}],"action":"","property":"","from":"","to":"","reg":false,"x":460,"y":660,"wires":[[]]},{"id":"2af95a3.2b46fa6","type":"change","z":"ec2c2ba0.1671a8","name":"Set consumption","rules":[{"t":"set","p":"consumption","pt":"flow","to":"payload","tot":"msg"}],"action":"","property":"","from":"","to":"","reg":false,"x":470,"y":740,"wires":[[]]}]
```