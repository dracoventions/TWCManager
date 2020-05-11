# cancelChargeNow API Command

## Introduction

The cancelChargeNow API command allows you to instruct TWCManager to stop charging under the ChargeNow policy, and revert to the existing policy.

## Format of request

The cancelChargeNow API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X POST -d "" http://192.168.1.1:8080/api/cancelChargeNow
```
