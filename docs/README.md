# TWCManager Documentation

## Having Trouble?

If you're having trouble getting TWCManager working, check out our [Troubleshooting Guide](Troubleshooting.md) to see if any of our tips help you out!

## Physical (RS-485) Installation

Please see the [Installation Guide](InstallationGuide.md) for detailed information on the installation of the Tesla Wall Connector interface to TWCManager.

## Software Installation

The following options exist for installing TWCManager:

   * [Docker](Software_Docker.md) - Docker uses containers to run applications in their own isolated environment. The benefits of docker include simple upgrading easy portability, with significantly less worries about Python versions or permissions in a Dockere environment than a Manual environment.

   * [Manual](Software_Manual.md) - A manual installation involves downloading the source code for TWCManager from GitHub, installing dependencies and then running TWCManager as a service.

### Configuration

The TWCManager configuration file at ```/etc/twcmanager/config.json``` has lots of information about each of the configuration parameters and their effect on your installation. We highly recommend reading through the file carefully as you configure your installation, as this resolves the majority of issues.

   * In addition, we have a set of [Configuration Examples](config_examples.md) intended to help with more complex setups such as those utilizing Flex Charging. These examples help to share information that has been discussed previously when setting up more complex charging policy.

## Developing for TWCManager

Your contributions are most welcome! If you've been working on a new EMS module or you want to contribute to the project in any way, please take a look at our [Development Guide](DevelopmentGuide.md) and feel free to get involved!

## Frequently Asked Questions

### How many units can be set up in this fashion?

The TWC Load Balancing protocol allows for up to four units within a group. As we are occupying one of the TWC Load Balancing unit IDs in order to provide the Master control of the charger group, there may be a total of three other units connected. When connecting additional units, they should be chained from the unused (In or Out) RS-485 terminals of the unit that is currently connected to TWCManager, which will allow all (up to) three of the units to be managed by one TWCManager instance.

### What can I do if my TWC is showing a red light blinking on the front of the unit?

This is because it has identified an error. If this occurred after starting the TWCManager.py script, it is highly likely that it has been caused by the TWCManager script.

Check the output of the TWCManager.py script. This will show you the reason for the error if it has been detected by the script. For example, if your rotary switch has not been adjusted to make the TWC a slave unit, you will see the following warning:

```
03:38:12 ERROR: TWC is set to Master mode so it can't be controlled by TWCManager.  Search installation instruction PDF for 'rotary switch' and set switch so its arrow points to F on the dial.
```

Similarly, if you are not running the TWCManager.py script and your TWC is set to Slave Mode, the same error condition will be shown via the TWC blinking red LED. In both cases, the error code is green: solid and red: 4 blinks. If you have any other error condition shown, refer to the table in your TWC user guide for specific details.

### Why is my car only charging at 6A?

There are a few reasons why you might see your car charging only at 6 amps:

  * There is less than 6A worth of generation capacity available
     * In this case, the charger will charge at 6A (2kW), as charging below this rate is of no benefit - it would not be sufficient to power the battery conditioning, and would be very inefficient as most of the power would be lost.
     
  * Your configuration has not been modified from the default
     * There are some safe defaults used in the config.json which ships with TWCManager. In particular:
        * wiringMaxAmpsAllTWCs: The maximum number of amps that all slave TWCs are able to draw simultaneously from the shared power source. Because a load-balanced TWC installation involves each of the TWCs sharing the same power feed, we need to configure a maximum allocation of current for all connected TWCs. This is set to 6A by default.
        * wiringMaxAmpsPerTWC: The maximum number of amps that each individual TWC is capable of drawing. If you think of the previous value (AllTWCs) as the capacity of the trunk power source that all TWCs are drawing from, this value (PerTWC) is the capability of each indiviual TWC, based on the wire gauge between the shared power source and the individual TWC. In a single TWC installation, this will be equal to the value of wiringMaxAmpsAllTWCs.
        
  * Conflict between Charger Consumption and Consumption Sensor
     * There are two ways in which your charger may be wired in an environment where you are able to access a consumption sensor:
        * The charger may be monitored as part of the consumption meter.
        * Your charger may not be monitored as part of the consumption meter.
     * If your charger is not monitored by the consumption meter, you do not need to make any changes to the default configuration. This configuration assumes that when you access consumption data, it does not count the charging load.
     * If your charging load/draw is counted by the consumption meter, this would cause the charger to be consistently forced down to 6A, as all of the generation would be canceled out by the power you draw to charge the vehicle.

### Why 6A?

   * 6A is the default minAmpsPerTWC setting. 
   * Charging at 240V 5A wastes 8.6% more energy than charging at 240V 10A.
      * Because of this, it is important to find a point at which you are comfortable setting a floor for charging current. If this is set too low, it will be inefficient. 

### Why doesn't charging stop when Solar generation drops below minimum

   * There are a few different ways in which we can stop a car from charging on a TWC:

      * V1 Chargers

The first revision of TWC chargers were able to stop charging by setting the maxAmps value to 0 amps. This is not effective for newer TWC chargers, however.

      * Stop communicating with the Slave TWCs. 
      
This is effective, in that stopping communications with a Slave TWC will stop the car from charging. Unfortunately the byproduct of this is that this can sometimes result in the car going into an error state, where charging can only be restarted by unplugging and replugging the TWC.

In an upcoming release, this will be offered as a switchable option to replace the use of Tesla API keys for those who are not comfortable with providing their credentials to the script.
      
      * Use the Tesla API to connect to the car, sending a command to stop/start charging.

This is set up using the web interface. Log in with your Tesla login and password, and the login token will be stored locally within a settings file.

If you have multiple cars, TWCManager will attempt to identify which cars are home using geofencing. The following page of the TMC forums thread explains it better than I could: https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830/page-16

### Why do I need to log into my Tesla account when using the web interface?

   * TWCManager uses your Tesla login to obtain an API token. This API token is used to talk to your vehicle(s).
   * When the available charger capacity falls below minAmpsPerTWC, the TWCManager script will contact the Tesla API to tell the vehicle to stop charging. If this is not configured, your vehicle will continue to charge at 6A even when the charging policy dictates that we stop charging.

### Why does my TWC increase charging momentarily to 21A or 17A around the time that it changes charging rates?

There are a number of reasons for this:

   * In the 2017.44 firmware version Tesla released around October 2017, a bug was introduced which led to vehicle charging rates falling to 6A when charging rates were raised. This is resolved by spiking the amps.

### Why is it so hard to just stop a vehicle from charging?

Good question:

   * Version 1 of the TWC protocol (for TWCs produced prior to and during early 2017) has a command which will cleanly stop charging Tesla vehicles.

   * For Version 2 TWCs produced after this time, there is no single approach which cleanly stops a Tesla vehicle from charging, without the vehicle itself wanting to stop charging. The options that exist are:

      * Ask the vehicle to stop charging by sending a message via the Tesla vehicle API (obviously a Tesla-only approach)

      * Stop communicating with the TWC for 30 seconds or more. This method stops the connected vehicle from charging, and will resume charging once the communications resume, however doing this a number of times will cause the vehicle to give up and the only way to resume charging is to unplug and replug the vehicle.

      * Sending the Stop message to Slave TWCs. This method will cause charging to cease immediately by instructing the TWC to open its relay, causing the charger to de-energise. A lack of CAN bus communication with the vehicle means that whilst the vehicle will stop charging immediately, it will log a number of errors and refuse to re-start charging again until it is unplugged and re-plugged (and will show a red LED ring around the charger port).

         * This method does work however if the DIP 2 switch is set in the **Down** position, which represents the use of legacy charge mode, which does not use CAN bus communication with Tesla vehicles. The usefulness of this configuration is equivalent to the "Stop communicating with slaves" behaviour above - it allows a number of stops and starts before the vehicle marks the charger as bad and refuses to charge until it is unplugged and re-plugged.

So in summary, the lack of a reasonable approach to stopping charging from the TWC side necessitates an API based solution.

### Why do only some people see vehicle VINs in the TWCManager interface?

This feature was only introduced in firmware version 4.5.3, which is found on TWCs manufactured from March 2018 until the end of 2019.

TWCs prior to this version will not respond to queries from TWCManager regarding the VIN of the vehicle connected. Unfortunately there is no sign that newer TWC firmwares are being installed by Tesla vehicles, and the TWCs themselves do not have internet access to upgrade themselves.

### What do we know about the various different Tesla Wall Charger revisions and how they operate?

   * The Tesla HPWC (Gen 1) wall charger was released in 2012 and was sold up until 2016, and can be identified by the LED. The Gen 1 used a bank of 4 DIP switches to configure the supplied amperage, rather than the rotary switch, and does not feature an RS458 bus at all. Gen 1 HPWC chargers are not capable of load sharing and cannot be used with TWCManager.
   * The Tesla TWC (Gen 2) wall charger was released in 2016 and was sold up until 2020, and differs only slighly from the Gen 1 from a visual perspective. The Gen 2 TWC provided better thermal management for the charger cable (an issue on older HPWCs) and better outdoor enclosure sealing, and introduced the charger load sharing protocol that this project uses.
   * The TWC Gen 3 wall charger was released in January 2020 and is still being sold today, and can be identified by the white faceplate and the shorter charging cable. The Gen 3 TWC has a single RS485 header (whereas the Gen 2 has a double RS485 header) and does not currently have sharing capability. It has the capability to connect to WiFi, however the value of this is not yet known.
