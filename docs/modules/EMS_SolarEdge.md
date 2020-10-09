# SolarEdge EMS Module

## Introduction

The SolarEdge EMS Module allows energy generation to be fetched from the SolarEdge API (```monitoringapi.solaredge.com```), which is a hosted management portal for SolarEdge inverters.

The module supports fetching generation values via the ```summary``` API, with efforts to fetch consumption via the ```siteCurrentPowerFlow``` API underway.

### A note about API Limits

Currently, SolarEdge's API interface limits users to 300 API requests per day. At a rate of one query per 90 seconds (which is what we limit the request rate to in this module), you are able to query for 7.5 hours per day.

Within the module itself, when you first start TWCManager, you might find the resolution of your generation rate is lower than after the first 5 polls, if you do not have a consumption meter. This is because:

   * The SolarEdge API publishes two endpoints, one with a high resolution generation value and no consumption, and one with a low-resolution generation and consumption value.
   * For the first 3 polls, we always use the low resolution endpoint while we measure if your installation provides a consumption value or not.
   * At this point, the module will either remain with the lower resolution endpoint with consumption support, or switch back to the higher resolution endpoint if no consumption value exists.

Perhaps in future if the API query limits are more generous, we could both drop the cache time and query both endpoints to enhance the experience, but this is about the best mid-point of functionality vs usability we can offer.

## Configuration

The following table shows the available configuration parameters for the SolarEdge EMS Module:

| **Parameter** | **Value** |
| ------------- | --------- |
| debugFile     | *optional* When used with the ```debugMode``` parameter below, specifies the location of the debug log file that SolarEdge generates. Default is ```/tmp/twcmanager_solaredge_debug.txt```. Make sure twcmanager has permissions to write to the directory/file. |
| debugMode     | *optional* If set to 1, enables Debug Logging which logs every request and reply to/from the SolarEdge API for analysis by developers. Set to 0 by default. |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the SolarEdge API |
| pollMode      | *optional* Allows a static definition of which poll mode to use. The default is 0 (auto-detect) however this can be set to 1 (non-consumption) or 2 (consumption) |
| apiKey        | *required* The API Key assigned when creating a new SolarEdge account via the portal. |
| siteID        | *required* The site ID assigned when creating a new SolarEdge account via the portal. |

Please note, if any of the required parameters for the SolarEdge EMS module are not specified in the module configuration, the module will unload at start time.

## JSON Configuration Example

```
"SolarEdge": {
  "enabled": true,
  "apiKey": "abcdef",
  "siteID": "ghijec",
  "debugMode": false
}
```

## Debugging

To debug the SolarEdge EMS module, you are recommended to run the module at debugLevel 4. This will print an error message if:

   * Any exception is triggered when trying to update the SolarEdge consumption value (however the actual exception will be printed at debugLevel 10).
   * If the current generation value (under <currentPower><power>) is not found in the XML returned by the SolarEdge API.

If these messages are not sufficient to find an issue with the module, please use the ```debugMode``` parameter. 
