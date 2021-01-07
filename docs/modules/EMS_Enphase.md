# Enphase Envoy EMS Module

## Introduction

Enphase Inverters provide either cloud-based or local API access, which allows querying of Solar Generation information.

This module supports either the querying of the public web-based API, or querying of the local inverter API, depending on the configuration supplied.

## Configuration

The following table shows the available configuration parameters for the Enphase EMS module.

### Cloud API Configuration

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the Enphase API. |
| systemID    | *required* The System ID allocated to your Enphase Envoy inverter. |
| userID      | *required* The User ID allocated to your Enphase Envoy installation. |

### Local API Configuration

| Parameter   | Value         |
| ----------- | ------------- |
| enabled     | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the Enphase API. |
| serverIP    | *required* The IP address of the Enphase Envoy Inverter. We will poll this device's HTTP API. |
| serverPort  | *optional* Defaults to Port 80. |


### JSON Configuration Example

#### Cloud API

```
"Enphase": {
  "enabled": true,
  "apiKey": "abcdef",
  "systemID": 1234,
  "userID": 1234
}
```

#### Local API

```
"Enphase": {
  "enabled": true,
  "serverIP": "192.168.1.2",
  "serverPort": 80
}
```
