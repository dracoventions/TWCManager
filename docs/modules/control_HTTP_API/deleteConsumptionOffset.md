# deleteConsumptionOffset API Command

## Introduction

The deleteConsumptionOffset API command requests TWCManager to delete an existing consumption offset.

## Format of request

The deleteConsumptionOffset API command is accompanied by a payload which describes the offset that you are deleting. The following example payload shows a request to delete an offset called WattsOffset:

```
{
  "offsetName": "WattsOffset",
}
```

An example of how to call this function via cURL is:

```
curl -X POST -d '{ "offsetName": "WattsOffset" } http://192.168.1.1:8080/api/deleteConsumptionOffset

```

This would instruct TWCManager to delete the offset described above.
