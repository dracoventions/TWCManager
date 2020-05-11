# chargeNow API Command

## Introduction

The chargeNow API command allows you to instruct TWCManager to start charging at a given rate, for a given period of time.

## Format of request

The chargeNow API command should be accompanied by a JSON-formatted request payload, specifying the rate to charge at and the time to charge for. The following is an example of a valid chargeNow payload:

```
{
  "chargeNowDuration": 3600,
  "chargeNowRate": 8
}
```

This would instruct TWCManager to charge for 1 hour at 8A.

An example of how to call this function via cURL is:

```
curl -X POST -d '{ "chargeNowRate": 8, "chargeNowDuration": 3600 }' http://192.168.1.1:8080/api/chargeNow
```
