# saveSettings API Command

## Introduction

The saveSettings API command instructs TWCManager to save the current settings dictionary stored in memory to disk.

You could use this command after modifying settings (using the setSettings API call) if you would like those changes to be persistent. We don't automatically change settings after calling setSettings as this uses write cycles on flash disk, hence separation of the ability to call setSettings and to save these settings.

## Format of request

The saveSettings API command is not accompanied by any payload. You should send a blank payload when requesting this command.

An example of how to call this function via cURL is:

```
curl -X POST -d "" http://192.168.1.1:8080/api/saveSettings
```
