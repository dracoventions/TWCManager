# TWCManager

## How it works

* This script (TWCManager) pretends to be a Tesla Wall Charger (TWC) set to master mode.
* When wired to the IN or OUT pins of real TWC units set to slave mode (rotary switch position F), TWCManager can tell them to limit car charging to any whole amp value between 5A and the max rating of the charger. Charging can also be stopped so the car goes to sleep.
* This level of control is useful for having TWCManager track the real-time availability of green energy sources and direct the slave TWCs to use near the exact amount of energy available. This saves energy compared to sending the green energy off to a battery for later car charging or off to the grid where some of it is lost in transmission (and costs are greater than charging off generated solar).

## Warnings

It is important to read and understand the following warnings before using this tool:

* Misuse of the protocol described in this software can direct a Tesla Wall Charger to supply more current to a car than the charger wiring was designed for.
* This will trip a circuit breaker or may start a fire in the unlikely event that the circuit breaker fails.
* This software was not written or designed with the benefit of information from Tesla and there is always a small possibility that some unforeseen aspect of its operation could damage a Tesla vehicle or a Tesla Wall Charger.
* All efforts have been made to avoid such damage and this software is in active use on the author's own vehicle and TWC.
* In short, USE THIS SOFTWARE AT YOUR OWN RISK.

## Features
* Can be set up to only allow charging during certain hours.
* Lets you control the amount of power delivered by a Tesla Wall Connector (TWC) to the car it's charging.
This can save around 6kWh per month when used to track a local green energy source like solar panels on your roof.  It can also avoid drawing grid energy for those without net metering or limit charging to times of day when prices are cheapest.
* Whilst the TWCManager application cannot read the charge state of connected vehicles, using the Tesla API we can pull 
* Integrates with HomeAssistant to read sensor data from Solar sensors, allowing both generation and consumption to be tracked and used in calculating charging rate
* Integrates with HomeAssistant to report TWC sensor data back to HomeAssistant for display or use in automations.

## Limitations
Due to hardware limitations, TWCManager will not work with Tesla's older High Power Wall Connectors (HPWCs) that were discontinued around April 2016.

## Installation
See docs/**TWCManager Installation.pdf** for how to install and use.

### Clone GIT Repository and copy files
```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager && make install
```

# Attribution
* Original TWCManager distribution by [cdragon](https://github.com/cdragon/TWCManager)
* Integrated improvements from [flodom's](https://github.com/flodorn/TWCManager) TWCManager fork. 
    * Support for multiple vehicles on multiple chargers
    * Support for publishing status to MQTT topics
