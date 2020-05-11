# sendStopCommand API Command

## Introduction

The sendStopCommand API command instructs TWCManager to send a stop command to all connected Slave TWCs.

**Note**: The stop command sent will instruct all vehicles connected to immediately stop charging. They will not re-attempt charging if they are a Tesla vehicle until they are re-connected to the TWC.

## Format of request

The sendStopCommand API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X POST -d "" http://192.168.1.1:8080/api/sendStopCommand
```
