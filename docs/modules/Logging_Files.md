# File Logging

## Introduction

The File logging module the debug information and statistical information which are printed to the console on a regular basis to a set of Log files in a directory specified in the configuration file.

This module is disabled by default. You might want this module enabled in your environment so you can log real-time status updates as vehicles charge, retaining that information locally.

A new file will be created every hour. The files are deleted after 24 hours.

Use this logging with care, it can break you SD card.

## Configuration Options

The following options exist for this Logging module:

| Option  | Example  | Description |
| ------- | -------- | ----------- |
| enabled | *false*  | Boolean value determining if the logging module should be activated. The default is *false*. |
| path    | */etc/twcmanager/log* | *required* A path to create the log files under. Make sure you make this path writable to the user that TWCManager runs as. |

### Muting Logging Topics

Logging modules allow for the individual toggling of certain topics to filter output. This is entirely optional and will default to output of all topics if it does not exist under the module's configuration. Below are the topics that may be toggled:

```
"mute":{
   "ChargeSessions": false,
   "GreenEnergy": false,
   "SlavePower": false,
   "SlaveStatus": false,
   "DebugLogLevelGreaterThan": 1
}
```

Setting a topic to true will cause that topic's output to be muted. With the DebugLogLevelGreaterThan parameter you can define which levels of debug information you want to write into the file. As higher the value, the more info will be written to the file (values between 0 and 12). 0 will mute the debug information completely.

### Example Configuration

Below is an example configuration for this module.

```
"logging":{
   "FileLogger": {
      "enabled": true,
      "path": "/etc/twcmanager/log",
      "mute":{
         "ChargeSessions": false,
         "GreenEnergy": false,
         "SlavePower": false,
         "SlaveStatus": false,
         "DebugLogLevelGreaterThan": 8
      }                 
   },
```
