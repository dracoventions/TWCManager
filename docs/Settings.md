# Settings

The following settings (outside of the configuration file) are available via the inbuilt Web Interface:

## Web Interface Theme

Allows you to select which theme you'd like to use for the TWCManager interface.

## Stop Charging Method

This option, which defaults to using the Tesla API, allows you to specify how you would like TWCManager to stop a car from charging. The following options exist, and each has some information to help you decide on which approach to use:

   * Tesla API
      * This method will use the Tesla API to send a stop charging message to vehicles which are detected as being "at home".
      * This method is only effective for Tesla vehicles. Any non-Tesla vehicles are not visible via the Tesla API and will not be stopped, even if the available power falls below the minimum power per TWC.
      * For those vehicles, they will continue to charge, but at the minimum power per TWC rate.
   * Stop Responding to Slaves
      * This method will cause TWCManager to stop responding to Slave TWCs when the allocated amps per TWC falls below the minimum amps per TWC value. It takes approximately 30 seconds from the moment that we stop responding to slaves until they stop charging connected vehicles.
      * This has the effect, if any vehicle is connected (not just Tesla vehicles) of stopping the TWC from offering charge to a vehicle. The green light on the TWC will remain steady, whilst the red light will blink on the TWC whilst the communication ceases, and no updates will be recieved from a TWC for that period of time.
      * For non-Tesla vehicles, this has the effect of stopping them from charging. It is not known on a per-vehicle basis (until more information is submitted) what the behaviour of those vehicles are.
      * For Tesla vehicles, this method is effective up to three times during a single charging session. The vehicle will allow this until the third instance, at which point it will refuse to resume charging until it is unplugged and re-plugged.
   * Send stop command
      * For TWCs running version v4.5.3 or later, there is a stop command embedded in the Firmware. The stop command appears to take the approach of disconnecting the relay, without sending any CAN bus messages.
      * With the DIP switch in position 1 (CAN protocol enabled), this has the unfortunate outcome for Tesla vehicles of entirely stopping the vehicle from charging immediately on reciept of the message. 
      * With the DIP switch in position 2 (CAN protocol disabled), it will stop Tesla vehicles from charging, but the vehicle will eventually (after a number of interruptions) decide that the charger is broken and will refuse to start charging again.
      * [This thread](https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830/page-24) provides the observations of those who have tested this command.
      * Whilst this option is offered primarily for the benefit of non-Tesla vehicles, it's not recommended for use with Tesla vehicles.

### Non-Scheduled Power Action & Charge Rate

This setting determines what TWCManager should do if there is no scheduled charging rate and outside of the Track Green Energy hours. The available options are:

      * Charge at specified Non-Scheduled Charge Rate

This option will allow vehicles to charge outside of Scheduled and Track Green Energy timings at the specified charge rate. This is the default setting (and the default Charge Rate is 6A).

      * Do not Charge

The Do not Charge action states that outside of scheduled or Track Green Energy hours, the TWCManager should set the available amps to 0 for Non-Scheduled Charging.

      * Track Green Energy

This is an option that currently does not operate (and will only set Non-Scheduled Charging rate to 0). In future, this will allow continuing of Track Green Energy behaviour outside of the hard-coded daylight hours (6am - 8pm).

### Charge Authorization Mode

The Charge Authorization Mode determines how we determine if a vehicle that starts to charge from a TWC should be allowed to do so. There are two options available:

   * Vehicles can charge unless explicitly blocked

This setting is the default, and specifies that any vehicle which requests to start charging can do so, unless it is explicitly added to the Deny Charging group.

   * Vehicles can only charge if explicitly allowed

This setting specifies that any vehicle which requests to start charging will be blocked, unless it has been added to the Allow Charging group.

### Consumption Offsets

Consumption Offsets are values which are applied to the Consumption value retrieved from EMS modules. Consumption Offsets can be either positive or negative values, and are often used to control the behaviour of TWCManager by making it appear as though the consumption is higher or lower than it is, or allows specifying an average consumption value for installations where it is not possible to query consumption data.

The value supplied can be:

   * Expressed in Amps. This is internally converted into watts by TWCManager, by multiplying with the current grid voltage, meaning the actual applied value of this offset will vary with voltage variations.
      * You would use an offset in Amps if you wanted to express an offset in circuit capacity - for example, if you already have a 1A load on a 20A circuit which is not metered, specifying +1A of consumption offset will treat that 1A as metered consumption.

   * Expressed in Watts. This allows for a specific power value to be specified. There will be no variance to offsets expressed this way.
      * You might use an offset like this to control the way that you treat Generation and Consumption data from Solar installations. For example, if you wanted to reduce the value measured from a Solar Array by 500W, you could add 500W of consumption via an offset.

This is most often given a value equal to the average amount of power consumed by everything other than car charging. 

For example, if your house uses an average of 2.8A to power computers, lights, etc while you expect the car to be charging, you could add an offset of 2.8A.

If you have solar panels, look at your utility meter while your car charges.

If it says you're using 0.67kW, that means you could either:
   * Add an offset for 0.67kW * 1000 / 240V = 2.79A assuming you're on the North American 240V grid. 
   * Add an offset for 670W, which would universally treat that 0.67kW as consumption regardless of grid voltage.

In other words, during car charging, you want your utility meter to show a value close to 0kW meaning no energy is being sent to or from the grid.

If you are able to obtain consumption details from an energy management system, don't add consumption offsets (unless you need them for other purposes), as TWCManager will query your EMS to determine the power being consumed.

### Manual Tesla API key override

In some instances, you may prefer to obtain the Tesla API keys yourself. The main benefit of this approach is that you do not need to provide your Tesla username or password to TWCManager.

Another reason to use this feature might be as a temporary workaround if the Tesla authentication flow is changed or the TWCManager authentication function is faulty.

Note: Providing your Tesla username and password to TWCManager to automatically fetch your Tesla API access and refresh tokens does not put your credentials at significant risk as they are only used once to fetch the token before being destroyed, however there may nonetheless be a preference not to provide these credentials at all.

To obtain the key, you will need some knowledge of the Tesla API authentication flow. To assist with this, a <a href="http://registration.teslatasks.com/generateTokens">link</a> to a service which can assist you with this process is provided, however this does therefore require you to provide your credentials to that service. Otherwise, you may want to research the Tesla authentication flow and obtain the tokens yourself, or to obtain them from another application that you have previously authenticated to.

Providing any value for the Access or Refresh tokens will result in the current stored tokens being overridden with the value you supply. We don't perform any validation of the tokens and the previous values are lost. Back up your settings.json file prior to entering your token manually if you need to revert your settings.
