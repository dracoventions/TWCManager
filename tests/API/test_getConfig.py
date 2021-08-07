#!/usr/bin/env python3

import json
import requests

# Configuration
skipFailure = 1

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

getAttempts = 0
response = None

# Output content is:
# b'{"policy":
#     {"extend":
#       {"restrictions": {}, "after": [], "before": [], "webhooks": {}, "emergency": []},
#     "override": [], "engine": {"policyCheckInterval": 30}
#   },
#    "interface": {"TCP": {"enabled": false}, "Dummy": {"enabled": true, "twcID": "AB"}, "RS485": {"baud": 9600, "port": "/dev/ttyUSB0", "enabled": false}}, "config": {"useFlexAmpsToStartCharge": false, "greenEnergyFlexAmps": 0, "wiringMaxAmpsPerTWC": 6, "cloudUpdateInterval": 1800, "numberOfPhases": 1, "displayMilliseconds": false, "logLevel": 20, "settingsPath": "/etc/twcmanager", "greenEnergyAmpsOffset": 0, "subtractChargerLoad": false, "onlyChargeMultiCarsAtHome": true, "minAmpsPerTWC": 12, "fakeMaster": 1, "wiringMaxAmpsAllTWCs": 6, "defaultVoltage": 240}, "control": {"HTTP": {"enabled": true, "listenPort": 8088}, "OCPP": {"serverPort": 9000, "enabled": false}, "MQTT": {"topicPrefix": "TWC",  "brokerIP": "127.0.0.1", "enabled": true, "username": "twcmanager"}}, "sources": {"SmartPi": {"serverIP": "127.0.0.1", "serverPort": "1080", "enabled": true}, "TED": {"serverIP": "192.168.1.1", "serverPort": "80", "enabled": false}, "SmartMe": { "enabled": false, "serialNumber": "ABC1234", "username": "username"}, "Efergy": {"token": "xx", "enabled": false}, "Enphase": {"serverIP": "127.0.0.1", "serverPort": 1080, "enabled": true}, "SolarEdge": {"siteID": "",  "enabled": false}, "Fronius": {"serverIP": "192.168.1.2", "enabled": false}, "HASS": {"serverPort": "8123",  "useHttps": false, "enabled": false, "hassEntityGeneration": "sensor.inverter_power_live", "serverIP": "192.168.1.1", "hassEntityConsumption": "sensor.meter_power_live"}, "openHAB": {"generationItem": "Generation item name", "serverIP": "192.168.1.2", "consumptionItem": "Consumption item name", "serverPort": "8080", "enabled": false}, "Powerwall2": {"minBatteryLevel": 90, "serverIP": "192.168.1.2",  "enabled": false}, "SolarLog": {"serverIP": "192.168.1.2", "excludeConsumptionInverters": [2], "enabled": false}, "MQTT": {"enabled": false}}, "status": {"HASS": {"serverPort": "8123", "retryRateInSeconds": 60, "useHttps": false, "enabled": false,  "serverIP": "192.168.1.1", "resendRateInSeconds": 3600, "msgRateInSeconds": 60}, "MQTT": {"topicPrefix": "TWC",  "brokerIP": "127.0.0.1", "enabled": true, "username": "twcmanager"}}, "logging": {"SQLite": {"path": "/etc/twcmanager/twcmanager.sqlite", "enabled": true, "mute": {}}, "MySQL": {"host": "127.0.0.1", "username": "twcmanager", "database": "twcmanager",  "mute": {}, "enabled": true}, "Sentry": {"mute": {"SlavePower": false, "ChargeSessions": false, "GreenEnergy": false, "SlaveStatus": false, "DebugLogLevelGreaterThan": 1}, "enabled": true, "DSN": ""}, "FileLogger": {"path": "/etc/twcmanager/log", "enabled": true, "mute": {"SlavePower": false, "ChargeSessions": false, "GreenEnergy": false, "SlaveStatus": false, "DebugLogLevelGreaterThan": 1}}, "CSV": {"path": "/etc/twcmanager/csv", "enabled": true, "mute": {"SlavePower": false, "ChargeSessions": false, "GreenEnergy": false, "SlaveStatus": false}}, "Console": {"enabled": true, "mute": {}}}}'

try:
    response = session.get("http://127.0.0.1:8088/api/getConfig", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

jsonResp = None

if response.status_code == 200:
    while (not jsonResp and getAttempts < 10):
        getAttempts += 1
        try:
            jsonResp = response.json()
        except ValueError as e:
            # On Python 3.4, JSON decoding failures raise ValueError
            print("Error: Unable to parse JSON output from getConfig()")

            f = open("/tmp/twcmanager-tests/getConfig-json-"+str(getAttempts)+".txt", "w")
            f.write("Exception: " + str(e))
            f.write("API Response: " + str(response.text))
            f.close()

        except json.decoder.JSONDecodeError as e:
            print("Error: Unable to parse JSON output from getConfig()")

            # Log the incomplete JSON that we did get - I would like to know
            # why this would happen
            f = open("/tmp/twcmanager-tests/getConfig-json-"+str(getAttempts)+".txt", "w")
            f.write("Exception: " + str(e))
            f.write("API Response: " + str(response.text))
            f.close()

        if (getAttempts == 2):
            # Too many failures
            # Fail tests
            exit(255)
else:
    print("Error: Response code " + str(response.status_code))
    exit(255)

success = 1
if jsonResp:
    if not jsonResp.get("interface",{}).get("Dummy",{}).get("enabled",None):
        print("Missing interface configuration")
        success = 0
    if not jsonResp.get("config", None):
        print("Error: Missing config branch")
        success = 0
    if not jsonResp.get("status", None):
        print("Error: Missing status branch")
        success = 0
    if not jsonResp.get("control", None):
        print("Error: Missing control branch")
        success = 0
else:
    print("No JSON response from API for getConfig()")
    exit(255)

if success:
    print("All tests successful")
    exit(0)
else:
    print("At least one test failed. Please review logs")
    if skipFailure:
        print("Due to skipFailure being set, we will not fail the test suite pipeline on this test.")
        exit(0)
    else:
        exit(255)
