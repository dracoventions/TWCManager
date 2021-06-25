# sendStartCommand API Command

## Introduction

The sendStartCommand API command instructs TWCManager to send a Start Charging message to all connected Slave TWCs.

## Format of request

The sendStartCommand API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X POST -d "" http://192.168.1.1:8080/api/sendStartCommand
```
