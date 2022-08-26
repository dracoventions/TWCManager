# setSetting API Command

## Introduction

The setSetting API command provides an interface to directly specify TWCManager settings via the HTTP API.

The command effectively allows the configuration of any setting that is stored in the TWCManager settings.json file.

Please note that due to a lack of validation of input for this command, it is entirely possible to specify values which may cause TWCManager to behave in an unpredictable manner. It's always recommended to use dedicated API functions for controlling settings over direct settings manipulation where possible.

## Format of request

The setSetting command can manipulate one setting at a time. The request consists of two values, setting and value.

The following example shows how you could manipulate the Home Latitude value via the API.

```
{
  "setting": "homeLat",
  "value": 12345
}
```

An example of how to call this function via cURL is:

```
curl -X POST -d '{ "setting": "homeLat", "value": 12345 }' http://192.168.1.1:8080/api/setSetting
```
