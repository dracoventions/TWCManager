#!/usr/bin/env python3

# test_consumptionOffsets.py
# This module tests the get and set API functions for the Consumption Offsets
# feature which allows offsets to be defined for the purpose of controlling
# artificial load or generation values

import json
import random
import requests
import time

# Configuration
skipFailure = 1

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

values = {
  "elapsed": {},
  "expected": {},
  "response": {},
  "status": {},
  "target": {},
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

# Generate random offset values
values["target"]["ampsFirst"]  = random.randint(2, 6)
values["target"]["ampsSecond"] = 0
while (not values["target"]["ampsSecond"] or values["target"]["ampsFirst"] == values["target"]["ampsSecond"]):
    values["target"]["ampsSecond"] = random.randint(2, 6)

values["target"]["wattsFirst"]  = random.randint(100, 500)
values["target"]["wattsSecond"] = 0
while (not values["target"]["wattsSecond"] or values["target"]["wattsFirst"] == values["target"]["wattsSecond"]):
    values["target"]["wattsSecond"] = random.randint(100, 500)


# Test 1 - Call addConsumptionOffset with no arguments
values["expected"]["addConNoArgs"] = 400
values["tests"]["addConNoArgs"] = {}
try:
    response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset", timeout=30)
    values["elapsed"]["addConNoArgs"] = response.elapsed
    values["response"]["addConNoArgs"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at addConNoArgs")
    values["tests"]["addConNoArgs"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at addConNoArgs")
    values["tests"]["addConNoArgs"]["fail"] = 1

time.sleep(2)

# Get offsets prior to adding our random offsets
values["status"]["Before"] = getOffsets("getOffsetsBefore")

# Test X - Call addConsumptionOffset with positive first Amps offset
values["expected"]["addConAmpsFirst"] = 400
values["tests"]["addConAmpsFirst"] = {}

data = {
    "offsetName": "First Amp Offset Positive",
    "offsetValue": values["target"]["ampsFirst"],
    "offsetUnit": "A"
}

try:
    response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
        data=data, timeout=30)
    values["elapsed"]["addConAmpsFirst"] = response.elapsed
    values["response"]["addConAmpsFirst"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at addConAmpsFirst")
    values["tests"]["addConAmpsFirst"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at addConAmpsFirst")
    values["tests"]["addConAmpsFirst"]["fail"] = 1

values["status"]["AmpsFirst"] = getOffsets("getOffsetsAmpsFirst")

# Test X - Call addConsumptionOffset with negative second Amps offset
values["expected"]["addConAmpsSecond"] = 400
values["tests"]["addConAmpsSecond"] = {}

data = {
    "offsetName": "Second Amp Offset Negative",
    "offsetValue": (-1 * values["target"]["ampsSecond"]),
    "offsetUnit": "A"
}

try:
    response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
        data=data, timeout=30)
    values["elapsed"]["addConAmpsSecond"] = response.elapsed
    values["response"]["addConAmpsSecond"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at addConAmpsSecond")
    values["tests"]["addConAmpsSecond"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at addConAmpsSecond")
    values["tests"]["addConAmpsSecond"]["fail"] = 1

values["status"]["AmpsSecond"] = getOffsets("getOffsetsAmpsSecond")

# Test X - Call addConsumptionOffset with positive first watts offset
values["expected"]["addConWattsFirst"] = 400
values["tests"]["addConWattsFirst"] = {}

data = {
    "offsetName": "First Watt Offset Positive",
    "offsetValue": values["target"]["wattsFirst"],
    "offsetUnit": "W"
}

try:
    response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
        data=data, timeout=30)
    values["elapsed"]["addConWattsFirst"] = response.elapsed
    values["response"]["addConWattsFirst"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at addConWattsFirst")
    values["tests"]["addConWattsFirst"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at addConWattsFirst")
    values["tests"]["addConWattsFirst"]["fail"] = 1

values["status"]["WattsFirst"] = getOffsets("getOffsetsWattsFirst")

# Test X - Call addConsumptionOffset with negative second watts offset
values["expected"]["addConWattsSecond"] = 400
values["tests"]["addConWattsSecond"] = {}

data = {
    "offsetName": "Second Watts Offset Negative",
    "offsetValue": (-1 * values["target"]["wattsSecond"]),
    "offsetUnit": "W"
}

try:
    response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
        data=data, timeout=30)
    values["elapsed"]["addConWattsSecond"] = response.elapsed
    values["response"]["addConWattsSecond"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at addConWattsSecond")
    values["tests"]["addConWattsSecond"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at addConWattsSecond")
    values["tests"]["addConWattsSecond"]["fail"] = 1

values["status"]["WattsSecond"] = getOffsets("getOffsetsWattsSecond")

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

