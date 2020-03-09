# TWCManager Documentation

## Physical (RS-485) Installation

Please see the [Installation Guide](InstallationGuide.md) for detailed information on the installation of the Tesla Wall Connector interface to TWCManager.

## Software Installation

### Install Packages (Debian/Ubuntu/Raspbian)
```
sudo apt-get update
sudo apt-get install -y lighttpd php7.0-cgi screen git python3-pip
```

### Default to Python3

You may need to set python3 as your default python interpreter version on Debian/Ubuntu. The following command will set python 3.5 as your default interpreter. 

```
sudo update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2
```

You can check that this command has been successful by running ```python --version``` and checking that the version is python3.

### Clone GIT Repository and copy files
```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager
git checkout v1.1.7
make install
```

### Configure TWCManager
After performing the installation tasks above, edit the /etc/twcmanager/config.json file and customize to suit your environment.

### Running the script
Once the above steps are complete, start the TWCManager script with the following command:

```
python3 -m TWCManager
```

## Monitoring the script operation

After starting TWCManager, the script will run in the foreground and will regularly update with the current status. An example output is as follows:

```
11:57:49: **SHA 1234**: 00 00.00/00.00A 0000 0000  M: 09 **00.00/17.00A** 0000 0000
11:57:49: Green energy generates **4956W**, Consumption 726W, Charger Load 0W
          Limiting car charging to 20.65A - 3.03A = **17.62A**.
          Charge when above **6A** (minAmpsPerTWC).
```

   * SHA 1234 is the reported TWC code for each of the Slave TWCs that the Master is connected to.
   * The 00.00/00.00A next to the Slave TWC code is the current number of amps being utilised and the total number of amps available to that slave. The master divides the total amperage available for use between the connected slaves.

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
   * When the available charger capacity falls below minAmpsPerTWC, 
