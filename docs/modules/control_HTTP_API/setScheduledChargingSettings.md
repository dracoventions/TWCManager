# setScheduledChargingSettings API Command

## Introduction

You can save the scheduled settings via a POST request

## Format of request

The setScheduledChargingSettings API command should be accompanied by a JSON-formatted request payload, providing the data to set:

| Attribute            | Description |
| ---------------      | ------------------------------ |
| **startingMinute**   | Minutes from midnight scheduled charging time should start |
| **endingMinute**     | Minutes from midnight scheduled charging time should end |
| **flexStartEnabled** | If you want to let your car starts charging at the end of Scheduled Charging Time, you can set this to true. This works only for exactly one TWCManager connected. Please be sure, that the amps provided are the power which your car can obtain. For better results set you battery size with flexBatterySize. |
| **flexBatterySize**  | Battery size of your car - default to 100 (biggest battery size - so your car should really finished before your ending time)        |
| **amps**             | Charging Power you want to divide among the slaves. |


```
{ 
	"enabled": true, 
	"startingMinute": 1260,
	"endingMinute": 420,
	"monday": true,
	"tuesday": true,
	"wednesday": true,
	"thursday": true,
	"friday": false,
	"saturday": false,
	"sunday": true,
	"amps": 20,
	"flexBatterySize": 100,
	"flexStartEnabled": true	
}
```

This would enable your car to start charging automatically at the end of the Scheduled Time - it calculates the needed time by the battery size (takes 92%) and adds a quarter at the end. Unless you want to charge more than 98% then it adds another half an hour. 

An example of how to call this function via cURL is:

```
curl -X POST -d '{ 
	"enabled": true, 
	"startingMinute": 1260,
	"endingMinute": 420,
	"monday": true,
	"tuesday": true,
	"wednesday": true,
	"thursday": true,
	"friday": false,
	"saturday": false,
	"sunday": true,
	"amps": 20,
	"flexBatterySize": 100,
	"flexStartEnabled": true	
}' http://192.168.1.1:8080/api/setScheduledChargingSettings
```
