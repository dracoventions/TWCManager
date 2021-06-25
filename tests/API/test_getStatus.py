#!/usr/bin/env python3

import requests

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

#b'{"scheduledChargingStartHour": -1, "consumptionAmps": "0.00", "isGreenPolicy": "No", "scheduledChargingFlexStart": -1, "chargerLoadWatts": "0.00", "currentPolicy": "Non Scheduled Charging", "generationWatts": "0.00", "carsCharging": 0, "scheduledChargingEndHour": -1, "maxAmpsToDivideAmongSlaves": "0.00", "consumptionWatts": "0.00", "ScheduledCharging": {"tuesday": true, "monday": true, "flexStartingMinute": -1, "flexSaturday": true, "flexFriday": true, "saturday": true, "wednesday": true, "flexTuesday": true, "thursday": true, "flexWednesday": true, "flexSunday": true, "flexBatterySize": 100, "amps": 0, "flexEndingMinute": -1, "sunday": true, "flexThursday": true, "flexStartEnabled": 0, "enabled": false, "endingMinute": -1, "flexMonday": true, "friday": true, "startingMinute": -1}, "generationAmps": "0.00"}'

response = None

try:
    response = session.get("http://127.0.0.1:8088/api/getStatus", timeout=5)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

json = None

if response.status_code == 200:
    json = response.json()
else:
    print("Error: Response code " + str(response.status_code))
    exit(255)
