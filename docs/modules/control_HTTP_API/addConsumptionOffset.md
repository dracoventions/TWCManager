# addConsumptionOffset API Command

## Introduction

The addConsumptionOffset API command requests TWCManager to add a new consumption offset, or edit an existing consumption offset. The Primary Key is the name of the offset.

## Format of request

The addConsumptionOffset API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X POST -d "" http://192.168.1.1:8080/api/addConsumptionOffset

