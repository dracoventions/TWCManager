# SolarEdge EMS Module

## Introduction

The SolarEdge EMS Module allows energy generation to be fetched from the SolarEdge API (```monitoringapi.solaredge.com```), which is a hosted management portal for SolarEdge inverters.

## Configuration

The following table shows the available configuration parameters for the SolarEdge EMS Module:

| **Parameter** | **Value** |
| ------------- | --------- |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the SolarEdge API |
| apiKey        | *required* The API Key assigned when creating a new SolarEdge account via the portal. |
| siteID        | *required* The site ID assigned when creating a new SolarEdge account via the portal. |

Please note, if any of the required parameters for the SolarEdge EMS module are not specified in the module configuration, the module will unload at start time.

## JSON Configuration Example

```
"SolarEdge": {
  "enabled": true,
  "apiKey": "abcdef",
  "siteID": "ghijec"
}
```

## Debugging

To debug the SolarEdge EMS module, you are recommended to run the module at debugLevel 4. This will print an error message if:

   * Any exception is triggered when trying to update the SolarEdge consumption value (however the actual exception will be printed at debugLevel 10).
   * If the current generation value (under <currentPower><power>) is not found in the XML returned by the SolarEdge API.
