# Console Logging

## Introduction

The console logging module replaces existing functionality which was included in the TWCManager daemon for printing status information to the console.

This module is enabled by default. You might want this module enabled in your environment so you can monitor real-time status updates as vehicles charge.

## Configuration Options

There are currently no specific configuration options for this module, other than enabling or disabling the module, and muting certain messages, both of which are universal options for logging modules

| Option  | Example | Description |
| ------- | ------- | ----------- |
| enabled | *true*  | Boolean value determining if the console logging module should be activated. The default is *true*. |

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
    "Console": {
        "enabled": true
    }
```
