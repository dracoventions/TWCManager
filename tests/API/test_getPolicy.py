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

try:
    response = session.get("http://127.0.0.1:8088/api/getPolicy", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

jsonResp = None

if response.status_code == 200:
    while (not jsonResp and getAttempts < 3):
        getAttempts += 1
        try:
            jsonResp = response.json()
        except json.decoder.JSONDecodeError as e:
            print("Error: Unable to parse JSON output from getPolicy()")

            # Log the incomplete JSON that we did get - I would like to know
            # why this would happen
            f = open("/tmp/twcmanager-tests/getPolicy-json-"+str(getAttempts)+".txt", "w")
            f.write("Exception: " + str(e))
            f.write("API Response: " + str(response.text))

        if (getAttempts == 2):
            # Too many failures
            # Fail tests
            exit(255)
else:
    print("Error: Response code " + str(response.status_code))
    exit(255)

success = 1
if jsonResp:
    # Content tests go here
    success = 1
else:
    print("No JSON response from API for getPolicy()")
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
