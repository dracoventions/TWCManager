# ChangeLog

This document logs the changes per release of TWCManager.

## v1.3.0 - Latest Development Version

## v1.2.3 - 2021-08-10

  * **NOTE**: v1.2.3 contains a potentially breaking change for users of OpenWB or the Legacy Web Interface
     * As of v1.2.3, the Legacy Web Interface and its dependencies such as lighttpd and php are no longer installed by default.
     * Please see the documentation for instructions on how to install it, if required. Most users will not need this.
  * **NOTE**: Starting from v1.2.3, Modern theme is the default theme for TWCManager, unless configured otherwise.
  * **NOTE**: v1.2.3 introduces a dedicated user account for TWCManager. For Manual install, you'll need to run ```make install``` after upgrading.
  * (@Saftwerk) - Add both Generation and Consumption support to Volkszahler EMS module
  * (@VIDGuide) - Improvements to the Modern UI - Show charger load and offered amps, and open GitHub link in a new window.
  * (@VIDGuide) - Add SoC % to Modern UI interface, and display charge time indicator per TWC
  * (@VIDGuide) - Fixed Modern UI layout on mobile, added Stop Charge Now button and fixed Charge Now control spacing.
  * (@VIDGuide) - Add Timezone parameter to docker-compose files to allow specifying container timezone
  * (@the-dbp) - Added Growatt EMS module
  * (@jherby2k) - Align API and HASS Status module values
  * (@mvaneijken) - Add MySQL logging module Port parameter
  * (@ngardiner) - Refactor TWCManager structure to allow for entire project to be packaged into pypi packaging for easy install/upgrades
  * (@jherby2k) - Add IotaWatt EMS interface
  * (@mvaneijken) - Added P1 Monitor EMS module
  * (@jherby2k) - Add support for HomeAssistant integration
  * (@MikeBishop) - Add support for deleting tasks, avoid sending stop commands under some conditions to avoid unnecessary transitions

## v1.2.2 - 2021-06-09

  * (@ngardiner) - Added SmartPi EMS interface
  * (@Saftwerk, @ngardiner) - Added Volkszahler EMS interface
  * (@ngardiner) - Added functionality to Dummy module to emulate TWC communication to the point that Policy selection occurs
  * (@MikeBishop) - Implement Policy Shortcut function to allow Charge Now to take immediate effect
  * (@GMerg) - Added OpenWeatherMap EMS interface
  * (@ngardiner) - Added VIN Management functionality, where vehicles can be allowed or denied charging based on VIN. With this, we introduce the ability to define vehicle groups, with future functionality allowing policy settings to be applied to these groups.
  * (@ngardiner) - Addition of a debug interface which allows tuning advanced inner workings of TWCManager, and allows sending commands to TWCs.
  * (@ngardiner) - Added support for Tesla MFA authentication flows
  * (@MikeBishop) - Improve API error handling, removing transient error delays and replacing with an exponential backoff mechanism to avoid delaying other background tasks.
  * (@MikeBishop) - Added debounce dampening for situations where intermittent consumption spikes / loads cause TWC to start and stop charging frequently.
  * (@ngardiner) - Add new consumption offset handling which allows for dynamic configuration of offsets in Watts and Amps via web and API
  * Bugfixes
    * (@ngardiner) - Better handling of permissions issues when attempting to save settings.json - alerts user to check file permissions via Web Interface
    * (@ngardiner) - Fixed issue with logging errors when a certain exception is raised in the Snapshot History function
    * (@ngardiner) - Fixed issue with Modern web interface Charge Now setting not working
    * (@ngardiner) - Fix behaviour of Stop Responding to Slaves charge stop mode, by re-enabling slave communication after 60 seconds
    * (@ngardiner) - Fix issues with subtractChargerLoad when using one of the (few) EMS modules which only provide Generation values. Previously, we only subtracted the Charger Load from Consumption which doesn't work in Generation-only measurement environments.
    * (@leeliu) - Fix TWC ID display for Modern theme which was truncating trailing zeros
    * (@ngardiner) - Fix bug in Stop Responding to Slaves routine caused by incorrect reference to time function

## v1.2.1 - 2021-04-04

  * Added support for Kostal inverters (Pico/Plenticore) (thanks @hopfi2k)
  * Added support for smart-me.com inverter API
  * Added support for serving static files via the inbuilt HTTPControl web server (thanks @hopfi2k)
  * Adjust charger load calculation based on real power measurements (thanks @dschuesae)
  * Introduce Scheduled Flex Charging feature (thanks @dschuesae)
  * Introduce new FileLogging module to allow logging to text file (thanks @dschuesae)
  * Moved debug logging to Logging modules to allow logging to file, database or other targets
  * Updated legacy Web UI to allow all EU/US amp selections (thanks @dschuesae)
  * Fix Web UI favicon (thanks @hopfi2k)
  * Added support for web themes, to allow changing the web UI to alternate views
  * Added Phase 1 of Charge Scheduling support, with backwards compatible charge scheduling (finally...) in the new UI
  * Added support for local query of Enphase EMS systems (previously cloud-only)
  * Set the legacy web UI module (WebIPC) to disabled by default. Avoids an error when running as a service, and is about time given it is deprecated.
  * Expose all time properties to the policy module for evaluation (thanks @MikeBishop)
  * Impovements to policy page in Web UI to show the value of policy parameters (thanks @MikeBishop)
  * Move grace period functionality for vehicles connected prior to policy evaluation to the master module, which opens the door to policy evaluation based on vehicle arrival/VIN (thanks @MikeBishop)
  * Split and show the values of Charger Load and Other Load in console output when the Subtract Charger Load setting is enabled (thanks @mikey4321)
  * Added EMS module support for SmartMe API
  * Added EMS module for Efergy (thanks @juanjoqg)
  * Added Graph visualisation for supported Logging modules - MySQL currently (thanks @juanjoqg)
  * Updates to accomodate Powerwall authentication flow changes (thanks @MikeBishop)
  * Do not override the charge_amps set in a policy when running checkGreenEnergy, allowing for Green Energy tracking numbers to be updated when Charge Now or Scheduled Charging policies are active (thanks @MikeBishop)
  * Significant overhaul of logging module interface to utilize the python logger architecture rather than implementing our own infrastructure (thanks @tjikkun!)
  * When competing background tasks are submitted, update the existing task details rather than dropping it completely (thanks @MikeBishop)
  * Bugfixes
      * Add a sleep of 5 seconds when waking car up to avoid an infinite loop (thanks @dschuesae)
      * Fix a bug with the legacy web interface which causes the Resume Track Green Energy setting of None to fail. Also added a deprecation notice to the web interface to ensure people don't inadvertently use it over the modular interface.
      * Fixed the Enphase EMS module which was reporting generation values as consumption (thanks @integlikewoah)
      * Added fix to avoid exception if an incoming TWC message is passed as an immutable bytes object to the unescape_msg function
      * Fix for the Fronius EMS module to query at System context rather than Device context which was failing to work in some installations due to Device ID mismatch
      * Fix dummy interface to load in place of RS485 interface for testing (thanks @tjikkun)
      * Add routines to avoid errors when settings keys are not defined (thanks @tjikkun)
      * Kostal EMS module no longer loads if not configured (thanks @MikeBishop)

## v1.2.0 - 2020-10-09

  * Added systemd service definition (thanks @nean-and-i)
  * Polling of Vehicle VIN on detection of charging vehicle (for those firmwares which support it) and access to Vehicle VIN via Status modules and Web Interface
  * Various updates to documentation (thanks @MikeBishop and @neilrees)
  * Web interface now uses AJAJ for dynamic asyncrhonous updates rather than page refresh
     * This change additionally introduces new REST API commands 
  * Handling of module import issues such as modules not existing (thanks @AndySchroder)
  * Use actual mains voltage per phase as reported by some TWC firmwares (thanks @MikeBishop)
  * Report background thread exceptions to the console (thanks @neilrees)
  * Added history recording for Slave TWC amps offered, with API function to query average amp history (thanks @MikeBishop).
  * Added recording of charge sessions per vehicle VIN, with rudimentary total kWh consumed calculations.
  * Added support for SolarEdge API EMS Module, thanks to prototype provided by Picar on TMC Forums.
  * Improved HASS status updates - sets sensor class and unit (thanks @dschuesae)
  * Added a fallback Tesla API stop mechanism to reduce the charge limit if the stop command via Tesla API fails to stop the vehicle from charging. This only works when the SOC is 50% or higher due to limitations in the API (thanks @MikeBishop)
  * Added new Logging module support, which takes console messages and modularises them to allow output to other mechanisms such as CSV files or Databases.
  * Bugfixes
    * Fixed situation where fakeMaster == 2 installations do not recieve Status module lifetime kWh and voltage per phase readings [Backported to 1.1.8]
    * Fixed unnecessary 60 second delay to processing background queue introduced by lifetime kWh and voltage per phase polling [Backported to 1.1.8] (Thanks @MikeBishop)
    * Fixed a condition in which flex and alternative maximum clash on charging rate (thanks @MikeBishop)
    * Fixed a number of issues with voltage and amperage calculation (thanks @dschuesae)
    * Fixed error with scheduling via old web UI and day index (thanks @dschuesae)
    * Removed Track green energy non-scheduled charging action from old Web UI (as new policy engine is incompatible) and moved it to new Web UI to allow re-introduction.

## v1.1.8 - 2020-04-26

  * Significant improvements in Tesla Powerwall2 EMS module function and stability (thanks @MikeBishop)
  * New module instantiation system removing static references to most modules
     * Integration of Tesla Vehicle API into module architecture (thanks @MikeBishop)
  * Policy Handling improvements
     * Modularization of the Policy engine, with ability to add additional constraints to policy definitions and to perform OR comparisons in policy conditions (thanks @MikeBishop)
     * Make policy match operators case-insensitive (thanks @MikeBishop)
     * Re-order policy to avoid Track Green Energy overriding scheduled charging, and to add a new emergency policy entry point at the start of the policy (thanks @MikeBishop)
     * Addition of Policy Latching and Flex for advanced policy use-cases (thanks @MikeBishop)
     * Documentation explaining the policy system (thanks @MikeBishop)
  * Tesla API & Vehicle Improvements
    * Introduce vehicle SOC charge limiting per policy (thanks @MikeBishop)
    * Query Tesla API to fetch Stormwatch detection data (thanks @MikeBishop)
    * Improved Arrival/Departure detection via the Tesla API (thanks @MikeBishop)
    * Reduced vehicle wake events due to opportunistic wake calls (thanks @MikeBishop)
  * Improved logging system which clearly shows the module which produced the log message and the log priority.
  * Completed the modularization of the RS485 interface code to allow alternative interfaces, and introduced two new interface modules (Dummy and TCP)
  * Ensure that status output formula balances for improved readability (thanks @MikeBishop)
  * Formatting improvements for the built-in webserver
  * Add policy webhook support (thanks @MikeBishop)
  * Added support for the SolarLog EMS Module (thanks @dschuesae)
  * Added support for OpenHab EMS Module (thanks @Frajul)
  * Support for tracking lifetime kWh and voltage per phase of slave TWCs, this includes:
    * Publishing of new Status (HASS and MQTT) values for lifetime kWh and voltage per phase
    * Polling of this value for TWCs with newer firmwares that provide it
  * Implement Stop command for TWCs (not recommended, see linked documentation)
  * Bugfixes
    * Remove duplicate conditional check in TeslaAPI module (thanks @MikeBishop)
    * Clarify the polarity of amperage offset in configuration file (thanks @MikeBishop)
    * Fix message length restriction on newer firmwares (thanks @nean-and-i)
    * Fix lag between Green Energy fetch and evaluation (thanks @MikeBishop)

## v1.1.7 - 2020-03-09

  * Dropped the default policy check timer down to 30 seconds from 60 seconds after positive feedback on lower calculation intervals
  * Dropped cache time in all EMS modules down to 10 seconds to ensure that the lower calculation intervals work correctly
  * Added ability to override the policy check timer to set it to any value desired
  * Added ability to override the policy entirely from the configuration file (with caveat that this is not recommended)
  * Added ability to extend the policy at two points (before and after) to add extra rules in whilst retaining the rest of the policy
  * MQTT control command chargeNow will now accept a payload specifying the number of amps and duration to charge
  * Added support for remote debugging using the Python Visual Studio remote debugger (ptvsd) (thanks @MikeBishop)
  * Significant improvements to Powerwall2 EMS module including authentication fixes, addition of Operating State to module state tracking, fixing a HTTPS certificate validation issue and stability testing (thanks @MikeBishop)
  * Early framework for centralised module instantiation
  * Allow use of module parameters within policy rules (thanks @MikeBishop)
  * Added setup.py setuptools script, which will shortly become the recommended installation method
  * Bugfixes
     * Fixed an issue where the policy based charging rules could not access settings variables due to an error in string offset (thanks @AndySchroder).
     * Fixed a bug with debug output if the charger is configured to draw more amps than the wiring can handle (thanks @AndySchroder).
     * Fixed an issue with the debug web interface (WebIPC) which impacted sending custom commands to the TWC and recieving the result
     * Fixed the refresh image for the IPC web interface (thanks @notreallybob).
     * Fixed a situation where amp calculations can lead to a value of -1 due to previously used default values. Any amp related defaults are now 0, with exception handling for negative values.
     * Fixed an error in policy rule where green energy charging was offset by 1 hour (thanks @MikeBishop)
     * Fixed Powerwall2 authentication process (using cookies rather than Authorization header) (thanks @MikeBishop)

## v1.1.6 - 2020-02-02

  * Implement policy-based charging, where individual charging logic (for scheduled, non-scheduled, green energy and charge now logic) is now centralised.
    * Benefits of this approach:
      * Single point within the code where we set the amps to share.
      * Defined priority to ensure one case does not override another.
      * Lays foundation for future advanced use cases.
  * TeslaAPI: Add optional override to not instruct a vehicle to stop charging via Tesla API (if the policy would otherwise dictate this) if the vehicle SOC is below a defined (optional) minimum. This avoids excessive battery drain which may be harmful to the vehicle's battery. Instead of stopping the charge session, the vehicle will continue to charge at ```minAmpsPerTWC``` until minimum SOC is met (thanks @MikeBishop).
  * Powerwall2 EMS: Feature to limit charging when Powerwall2 state of charge is below a defined minimum, to avoid depleting Powerwall2 during low energy generation (thanks @MikeBishop).
  * Bugfix: HASS EMS module was non-functional due to an error introduced during config separation. Fixed in v1.1.6.
  * Bugfix: Makefile update to install php7.3 on raspbian (thanks @MikeBishop)
  * Bugfix: Fix typo which did not set desiredAmps to 0 when total amps available for all chargers was less than 1 (thanks @MikeBishop)
  * Bugfix: Fix crash condition in dumpState function for WebIPC control interface (thanks @MikeBishop)
  * Bugfix: Correctly display multiple chargers in web (RPC) interface (merged from upstream @cdragon)

## v1.1.5 - 2019-11-02

  * Standardised module configuration handling (which helps reduce the number of exceptions related to configuration)
  * Added configuration to enable/disable and configure HTTPControl module
  * Added Grid Status, Voltage and Password Authentication support to Tesla Powerwall2 EMS module
  * Tested and fixed TWCManager Slave Mode functionality

## v1.1.4 - 2019-10-22

  * Implemented Tesla login / token retrieval for HTTP Config module.
  * Improved debug logging for Tesla API Vehicle module.
  * Modularised the Web IPC interface for the external web server control component.
  * Fix: Status output now subtracts charger load from consumption.
  * Re-implemented the Tesla API queries using python's request module rather than external shell calls to curl. Provides better exception handling and less shell command/subprocess interaction.
  * Breaking Change: Improved Settings Storage for non-volatile settings (not configuration) storage. 
    * This will require a manual port of the settings from ```/etc/twcmanager/TWCManager.settings``` to ```/etc/twcmanager/settings.json```
    * Due to a small user base, this is not done automatically. If there is demand for a port method, an issue can be raised for a feature request, and I'll create a one time script to port old settings to new settings.

## v1.1.3 - 2019-10-17

  * Added new HTTP Control Module for (limited) in-built HTTP control of TWCManager.
  * Added new Tesla Powerwall 2 EMS module for solar/consumption tracking.
  * Separation of Slave TWC code from Master TWC code - this adds stability by r
emoving a large number of global variables and reduces complexity for future fea
ture improvements.
     * Please Note: This is a major structural change to TWCManager, and is expected to take some time to fully test and validate. A benefit of this change is that now TWCSlave is modular, we can fully implement modular control interfaces.

## v1.1.2 - 2019-10-14

  * Improvements to HomeAssistant EMS module to avoid setting Consumption/Generation values to zero as a result of a connection failure, and better exception handling in general for the module.
  * Added EMS support for TED (The Energy Detective)
  * Added Control module support with a first control module for MQTT, with initial commands to stop the TWCManager daemon and start charging immediately.
  * Improvements to the MQTT and HASS topic/sensor names for Slave TWCs. (4 byte instead of 2 byte)

## v1.1.0 - 2019-10-12

  * Separation of Tesla API class from TWCManager code, this allows pluggable modules for interfacing with vehicles.
  * Added Fronius EMS module - read generation and consumption values from a Fronius inverter.
  * Added MQTT authentication for MQTT Status module.
  
### Fixes

  * Fixed settings file location path which had issues if no trailing slash.

## v1.0.2 - 2019-10-11

  * Option to subtract charger utilization from consumption value if consumption meter is counting charger load.
  * Updated status output to more clearly define the generation and consumption values being tracked.

## v1.0.1 - 2019-10-06

This release is a bugfix release for v1.0.0. It contains the following fixes:

  * Fixed: MQTT status connection timeout causes a delay to heartbeat timers, which then cause TWCManager reconnections to Slaves
  * Fixed: MQTT and HASS status update rates are too high. All updates now rate limited to one per minute.

## v1.0.0 - 2019-10-05

This module provides HomeAssistant sensor functionality to the TWCManager project. It is the first release after the fork and restructuring of the code and configuration files.

  * Forked original repository by cdragon
  * Integrated multi-charger and multi-car MQTT integration (Status Module) from flodorn's repository
  * Split the Sensor (EMS) and Status functions out of the main script
  * Created HomeAssistant EMS and Status modules and tested successfully
