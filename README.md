# TWCManager

## Features
* Lets you control the amount of power delivered by a Tesla Wall Connector (TWC) to the car it's charging.
This can save around 6kWh per month when used to track a local green energy source like solar panels on your roof.  It can also avoid drawing grid energy for those without net metering or limit charging to times of day when prices are cheapest.
* Integrates with HomeAssistant to read sensor data from Solar sensors, allowing both generation and consumption to be tracked and used in calculating charging rate
* Integrates with HomeAssistant to report TWC sensor data back to HomeAssistant for display or use in automations.

## Limitations
Due to hardware limitations, TWCManager will not work with Tesla's older High Power Wall Connectors (HPWCs) that were discontinued around April 2016.

## Installation
See **TWCManager Installation.pdf** for how to install and use.

### Clone GIT Repository and copy files
```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager && make install
```

# Attribution
* Original TWCManager distribution by [cdragon](https://github.com/cdragon/TWCManager)
* Integrated improvements from [flodom's](https://github.com/flodorn/TWCManager) TWCManager fork. 
