# P1 Monitor EMS Module

## Introduction

The P1 Monitor (https://www.ztatz.nl/) EMS module allows fetching of Consumption and Production values from the P1 Monitor Phase API (/api/v1/phase).

## How it works

On each policy request this EMS module request data from the /api/v1/phase endpoint of your P1 Monitor taking a configurable number of samples. It receives both Consumption and Production data of each phase and will calculate a trimmed average (cutting of 10% of the minimum and maximum values) to get a value that is not influenced by any spikes on the net (e.g. a Quooker periodically heating up for a couple of seconds). By default the P1 Monitor API reports new values each 10 seconds, so when taking 6 samples it will give you an average Consumption/Production over 60 seconds.

Because we want to avoid overloading the net, we report the maximum average value of the phase that has the highest load for Consumption.

For the Production values we take a sum of all average values on each phase. This because the Consumption should always be within the technical fuse limitations on the net. So when you have a main fuse of 25Amps, the Consumption value should never be higher that 25Amps.

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | P1Monitor                      |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Production        |
| **Status**      | Development                    |

## Configuration

The following table shows the available configuration parameters for the P1 Monitor EMS module.

| Parameter   | Value         |
| ----------- | ------------- |
| serverIP    | *required* The IP address of the P1 Monitor instance. |
| samples  | *optional* The amount of samples to calculate with (default 1, min 1, max 10). |

### JSON Configuration Example

```
{
    "sources":{
        "P1Monitor": {
            "serverIP": "192.168.1.2",
            "samples": 1
        }
    }
}
```
