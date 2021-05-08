# getConsumptionOffsets API Command

## Introduction

The getConsumptionOffsets API command requests TWCManager to provide a list of Consumption Offsets configured.

## Format of request

The getConsumptionOffsets API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X GET -d "" http://192.168.1.1:8080/api/getConsumptionOffsets
```

