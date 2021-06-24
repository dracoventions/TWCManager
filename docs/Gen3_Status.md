# TWC Gen 3

## Introduction

This document serves as a repository of what we do and don't know about the TWC Gen 3. Starting with the key detail:

### It was released in Jan 2020

   * At release time it had no support for integration with any Green Energy sources including Tesla's Powerwall.
      * As of June 2021, that continues to be the case

   * It was initially released without any power sharing support at all (the feature that TWCManager uses to track solar generation for the Gen 2)
      * See here: https://www.tesla.com/support/gen-3-wall-connector-power-sharing
      * As of June 2021, a firmware version (21.18.1) has been released which supports Power Sharing between Gen3 units (**only**) using Mesh WiFi. This does not enable the RS485 pins and does not provide backward compatibility with the Gen 2 Power Sharing feature.
      * Thankfully, there is hope RS485 will make it into a later firmware release, as Tesla state: 

**Can I connect Gen 2 and Gen 3 Wall Connectors together in a power sharing network?**

No. This configuration is not **currently** available.

*(emphasis mine)*

### It does not work with TWCManager

Unfortunately, the TWC Gen 3 is not currently compatible with TWCManager. In its current form, it does not appear that it could be. That said...

   * The Gen 3 TWC physically possesses a single (vs the pair in the TWC Gen 2) RX/TX terminal for RS485
      * It does not appear to be activated. Owners of Gen3 units have connected RS485 adapters to their Gen3 RS485 terminals and 

   * The Gen 3 TWC **can** be configured via WiFi, including the maximum amps for the unit, but this is a First Time installation wizard and becomes unavailable after a period of time (~ 5 minutes reportedly), so it does not appear to be useful for this purpose

### It has WiFi, so it can receive over the air (OTA) updates

Which is good. This means that it's **possible** that Tesla will add the functionality we need in the future

### We will be able to talk to TWC Gen 3 units

   * But it is all read-only values at this time. We have no endpoint that allows us to modify anything, currently.

## A plea about being informative

It's concerning to see a lot of statements nowadays stating that the TWC Gen 3 will contain the capability to charge based on solar consumption due to WiFi connectivity.

We sincerely hope it's the case and plan to support it as soon as it is available.

However, today, it is not available and we have even less control over a TWC Gen 3 than a Gen 2. This is not buying advice, perhaps the Gen 3 is overall the better solution for you, but please be aware that if you buy one today, we both are not able to support it currently, 

### What are our plans?

The plans are:

   * Assess the value of the current API endpoints - they appear to be valuable for monitoring (but not controlling) a Gen 3 TWC.
   * Wait for backward compatibility TWC Gen 2 support from Tesla, keeping in mind that Power Sharing took 16 months to make it into the firmware in its current form. This would allow integration with the Gen 3 without modification to the code, assuming Tesla fully implement the Gen 2 protocol.
   * Consider if we could participate in the WiFi Mesh
      * We just don't know. This is all too new, it was released this month and we're not even sure how the Gen 3s integrate yet.

## More detailed analysis

Below is an analysis of Firmware 21.18.1, looking for details around connectivity and API endpoints that we might consume:


  * /tedapi/v1
  * /tedapi/din


  * /access
  * /alerts
  * /api/1/lifetime
  * /api/1/version
  * /api/1/vitals

```
{
  "contactor_closed":false,
  "vehicle_connected":false,
  "session_s":0,
  "grid_v":232.0,
  "grid_hz":50.020,"vehicle_current_a":0.4,"currentA_a":0.2,"currentB_a":0.4,"currentC_a":0.2,"currentN_a":0.3,"voltageA_v":0.0,"voltageB_v":4.9,"voltageC_v":0.0,"relay_coil_v":12.0,"pcba_temp_c":29.0,"handle_temp_c":22.1,"mcu_temp_c":34.9,"uptime_s":190,"input_thermopile_uv":-204,"prox_v":0.0,"pilot_high_v":11.9,"pilot_low_v":11.9,"session_energy_wh":0.000,"config_status":5,"evse_state":1,"current_alerts":[]}
```

  * /api/1/wifi_status

```
{
  "wifi_ssid":"redacted",
  "wifi_signal_strength":36,
  "wifi_rssi":-72,
  "wifi_snr":22,
  "wifi_connected":true,
  "wifi_infra_ip":"192.168.xxx.xx",
  "internet":true,
  "wifi_mac":"xx:xx:xx:xx:xx:xx"
}
```

  * /error/public
  * /error/unauthenticated
  * /fwupdate
  * /installation
  * /service
  * /sharing
  * /sharing/add
  * /sharing/settings
  * /update (triggers firmware update)
  * /wifi

## Useful References

   * https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830/page-26#post-4502118
   * https://www.tesla.com/support/gen-3-wall-connector-power-sharing
   * https://github.com/ngardiner/TWCManager/issues/292
   * https://teslamotorsclub.com/tmc/threads/gen3-wall-connector-api.228034/
