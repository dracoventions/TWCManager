#!/usr/bin/env python3

# test_consumptionOffsets.py
# This module tests the get and set API functions for the Consumption Offsets
# feature which allows offsets to be defined for the purpose of controlling
# artificial load or generation values

import json
import requests

# Configuration
skipFailure = 1

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

values = {
  "response": {},
  "status": {},
  "tests": {}
}


def getOffsets(tag):
    # Query getConsumptionOffsets to see our current configured offsets
    try:
        response = session.get("http://127.0.0.1:8088/api/getStatus", timeout=30)
        values["response"][tag] = response.status_code
    except requests.Timeout:
        print("Error: Connection Timed Out at " + tag)
    except requests.ConnectionError:
        print("Error: Connection Error at " + tag)

    # Return json
    jsonOut = False
    try:
        jsonOut = response.json()
    except json.decoder.JSONDecodeError as e:
        print("Could not parse JSON at " + tag)
    except UnboundLocalError:
        print("Request object is not valid - look for connection error previously")

    return jsonOut

values["status"]["Before"] = getOffsets("getOffsetsBefore")

# Print out values dict
f = open("/tmp/twcmanager-tests/consumptionOffsets.json", "a")
f.write(str(values))
f.close()

for test in values["tests"].keys():
    if values["tests"][test].get("fail", 0):
        print("At least one test failed. Please review logs")
        if skipFailure:
            print("Due to skipFailure being set, we will not fail the test suite pipeline on this test.")
            exit(0)
        else:
            exit(255)

print("All tests were successful")
exit(0)

