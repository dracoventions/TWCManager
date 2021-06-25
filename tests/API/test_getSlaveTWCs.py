#!/usr/bin/env python3

import requests

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

#b'{"4142": {"lastAmpsOffered": 0, "lastHeartbeat": 0.68, "state": 0, "TWCID": "4142", "voltsPhaseC": 0, "reportedAmpsActual": 0.0, "lastVIN": "", "maxAmps": 80.0, "lifetimekWh": 0, "version": 2, "currentVIN": "", "voltsPhaseA": 0, "voltsPhaseB": 0}, "total": {"lifetimekWh": 0, "reportedAmpsActual": 0.0, "TWCID": "total", "maxAmps": 80.0, "lastAmpsOffered": 0}}'
# Todo Tests:
#    Send specific lifetime kWh message and compare values

response = None

try:
    response = session.get("http://127.0.0.1:8088/api/getSlaveTWCs", timeout=5)
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

success = 1

if json:
    if not json["4142"]:
        success = 0
        print("Error: Could not find TWC 4142 in getSlaveTWCs() output")
    if json["4142"]["lastHeartbeat"] > 5:
        success = 0
        print("Error: TWC 4142 has not responded with heartbeat message in 5 seconds")
    if json["4142"]["maxAmps"] != 80:
        success = 0
        print("Detected Maximum Amperage for TWC 4142 is incorrect")
else:
    print("No JSON response from API for getConfig()")
    exit(255)

if success:
    print("All tests successful")
    exit(0)
else:
    print("At least one test failed. Please review logs")
    exit(255)
