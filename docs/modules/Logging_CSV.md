# CSV Logging

## Introduction

The CSV logging module outputs statistics which are printed to the console on a regular basis to a set of CSV files in a directory specified in the configuration file.

This module is disabled by default. You might want this module enabled in your environment so you can log real-time status updates as vehicles charge, retaining that information locally.

## CSV Files

The following CSV files will be created in the destination directory. Note that this is assuming none of the logging categories are muted. Muted categories will not be written out to file.

   * chargesessions.csv
      * Stores charge session information
   * greenenergy.csv
      * When green energy policy is in effect, logs the green energy generation and consumption data
   * slavestatus.csv
      * Logs Slave TWC status data - lifetime kWh and voltage per phase across al

## Configuration Options

The following options exist for this Logging module:

| Option  | Example  | Description |
| ------- | -------- | ----------- |
| enabled | *false*  | Boolean value determining if the CSV logging module should be activated. The default is *false*. |
| path    | */etc/twcmanager/csv* | *required* A path to create the CSV files under. Make sure you make this path writable to the user that TWCManager runs as. |

### Muting Logging Topics

Logging modules allow for the individual toggling of certain topics to filter output. This is entirely optional and will default to output of all topics if it does not exist under the module's configuration. Below are the topics that may be toggled:

```
"mute":{
   "ChargeSessions": false,
   "GreenEnergy": false,
   "SlavePower": false,
   "SlaveStatus": false
}
```

Setting a topic to true will cause that topic's output to be muted.

### Example Configuration

Below is an example configuration for this module.

```
"logging":{
    "CSV": {
        "enabled": true,
        "path": "/etc/twcmanager/csv"
    }
```
