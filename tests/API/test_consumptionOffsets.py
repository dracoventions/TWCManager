#!/usr/bin/env python3

# test_consumptionOffsets.py
# This module tests the get and set API functions for the Consumption Offsets
# feature which allows offsets to be defined for the purpose of controlling
# artificial load or generation values

import datetime
import json
import random
import requests
import time

# Configuration
skipFailure = 1
maxRequest = datetime.timedelta(seconds=2)
dummySettings = {
    "Voltage": 240
}

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

def addOffset(tag, data):
    global values

    try:
        response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
            json=data, timeout=30)
        values["elapsed"][tag] = response.elapsed
        values["response"][tag] = response.status_code
    except requests.Timeout:
        print("Error: Connection Timed Out at %s" % tag)
        values["tests"][tag]["fail"] = 1
    except requests.ConnectionError:
        print("Error: Connection Error at %s" % tag)
        values["tests"][tag]["fail"] = 1

def getOffsets(tag):
    try:
        response = session.get("http://127.0.0.1:8088/api/getConsumptionOffsets", timeout=30)
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

def setSetting(setting, value):

    data = {
      "setting": setting,
      "value": value
    }

    try:
        response = session.post("http://127.0.0.1:8088/api/setSetting", json=data, timeout=30)
        values["response"]["setSetting " + setting] = response.status_code
    except requests.Timeout:
        print("Error: Connection Timed Out at setSetting " + setting)
    except requests.ConnectionError:
        print("Error: Connection Error at setSetting " + setting)

# Generate random offset values
values["target"]["ampsFirst"]  = random.randint(2, 6)
values["target"]["ampsSecond"] = 0
while (not values["target"]["ampsSecond"] or values["target"]["ampsFirst"] == values["target"]["ampsSecond"]):
    values["target"]["ampsSecond"] = random.randint(2, 6)

values["target"]["wattsFirst"]  = random.randint(100, 500)
values["target"]["wattsSecond"] = 0
while (not values["target"]["wattsSecond"] or values["target"]["wattsFirst"] == values["target"]["wattsSecond"]):
    values["target"]["wattsSecond"] = random.randint(100, 500)

# Set initial Dummy module settings
setSetting("DummyModule", dummySettings)

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

# Test 2 - Call addConsumptionOffset with positive first Amps offset
values["expected"]["addConAmpsFirst"] = 204
values["tests"]["addConAmpsFirst"] = {}

data = {
    "offsetName": "First Amp Offset Positive",
    "offsetValue": values["target"]["ampsFirst"],
    "offsetUnit": "A"
}

addOffset("addConAmpsFirst", data)
values["status"]["AmpsFirst"] = getOffsets("getOffsetsAmpsFirst")

# Test 3 - Call addConsumptionOffset with negative second Amps offset
values["expected"]["addConAmpsSecond"] = 204
values["tests"]["addConAmpsSecond"] = {}

data = {
    "offsetName": "Second Amp Offset Negative",
    "offsetValue": (-1 * values["target"]["ampsSecond"]),
    "offsetUnit": "A"
}

addOffset("addConAmpsSecond", data)
values["status"]["AmpsSecond"] = getOffsets("getOffsetsAmpsSecond")

# Test 4 - Call addConsumptionOffset with positive first watts offset
values["expected"]["addConWattsFirst"] = 204
values["tests"]["addConWattsFirst"] = {}

data = {
    "offsetName": "First Watt Offset Positive",
    "offsetValue": values["target"]["wattsFirst"],
    "offsetUnit": "W"
}

addOffset("addConWattsFirst", data)
values["status"]["WattsFirst"] = getOffsets("getOffsetsWattsFirst")

# Test 5 - Call addConsumptionOffset with negative second watts offset
values["expected"]["addConWattsSecond"] = 204
values["tests"]["addConWattsSecond"] = {}

data = {
    "offsetName": "Second Watts Offset Negative",
    "offsetValue": (-1 * values["target"]["wattsSecond"]),
    "offsetUnit": "W"
}

addOffset("addConWattsSecond", data)
values["status"]["WattsSecond"] = getOffsets("getOffsetsWattsSecond")

# Test 6 - Call addConsumptionOffset with float value
values["expected"]["addConFloat"] = 204
values["tests"]["addConFloat"] = {}

data = {
    "offsetName": "Float Value",
    "offsetValue": 1.123456789012345678901234567890,
    "offsetUnit": "W"
}

addOffset("addConFloat", data)
values["status"]["addConFloat"] = getOffsets("getOffsetsFloat")

# Test 7 - Call addConsumptionOffset with non-Amp or Watt value
values["expected"]["addConInvalidUnit"] = 400
values["tests"]["addConInvalidUnit"] = {}

data = {
    "offsetName": "Offset with Invalid Unit",
    "offsetValue": 500,
    "offsetUnit": "Z"
}

addOffset("addConInvalidUnit", data)
values["status"]["addConInvalidUnit"] = getOffsets("getOffsetsInvalidUnit")

# Test 8 - Add offset with excessively long name
name = "Offset "
for x in range(0, 4096):
    name += str(x)

values["expected"]["addConLongName"] = 400
values["tests"]["addConLongName"] = {}

data = {
    "offsetName": name,
    "offsetValue": 5,
    "offsetUnit": "W"
}

addOffset("addConLongName", data)
values["status"]["addConLongName"] = getOffsets("getOffsetsLongName")

# Test 9 - Add offset with characters which may potentially break settings.json file
name = "Offset \":{},[],"

values["expected"]["addConBadName"] = 400
values["tests"]["addConBadName"] = {}

data = {
    "offsetName": name,
    "offsetValue": 5,
    "offsetUnit": "W"
}

addOffset("addConBadName", data)
values["status"]["addConBadName"] = getOffsets("getOffsetsBadName")

# Test 10 - Add offset with nul byte for name
values["expected"]["addConNulName"] = 400
values["tests"]["addConNulName"] = {}

data = {
    "offsetName": '',
    "offsetValue": 5,
    "offsetUnit": "W"
}

addOffset("addConNulName", data)
values["status"]["addConNulName"] = getOffsets("getOffsetsNulName")


# Test 11 - Add offset with nul byte for value
values["expected"]["addConNulValue"] = 400
values["tests"]["addConNulValue"] = {}

data = {
    "offsetName": "Null Value",
    "offsetValue": '',
    "offsetUnit": "W"
}

addOffset("addConNulValue", data)
values["status"]["addConNulValue"] = getOffsets("getOffsetsNulValue")

# Test 12 - Update all existing offsets (except Tests 7 or 8) by setting them all to 5A
for offsetName in [ "First Amp Offset Positive", "Second Amp Offset Negative", 
   "First Watt Offset Positive", "Second Watts Offset Negative" ]:
    runname = "Update " + offsetName

    values["expected"][runname] = 204
    values["tests"][runname] = {}

    data = {
        "offsetName": offsetName,
        "offsetValue": 5,
        "offsetUnit": "A"
    }

    try:
        response = session.post("http://127.0.0.1:8088/api/addConsumptionOffset",
            json=data, timeout=30)
        values["elapsed"][runname] = response.elapsed
        values["response"][runname] = response.status_code
    except requests.Timeout:
        print("Error: Connection Timed Out at %s" % runname)
        values["tests"][runname]["fail"] = 1
    except requests.ConnectionError:
        print("Error: Connection Error at %s" % runname)
        values["tests"][runname]["fail"] = 1

    values["status"][runname] = getOffsets("getOffsets" + runname)

# Test 11 - Delete all configured consumption offsets
offsets=getOffsets("DeleteAll")
for offset in offsets.keys():
    data = {
        "offsetName": offset
    }

    try:
        response = session.post("http://127.0.0.1:8088/api/deleteConsumptionOffset",
            json=data, timeout=30)
    except requests.Timeout:
        print("Error: Connection Timed Out at deleteConsumption")
        values["tests"]["deleteConsumption"]["fail"] = 1
    except requests.ConnectionError:
        print("Error: Connection Error at deleteConsumption")
        values["tests"]["deleteConsumption"]["fail"] = 1

values["status"]["deleteConsumptionAfter"] = getOffsets("deleteConsumptionAfter")

# For each request, check that the status codes match
for reqs in values["expected"].keys():
    if values["response"].get(reqs, None):
        if values["response"][reqs] != values["expected"][reqs]:
            print("Error: Response code " + str(values["response"][reqs]) + " for test " + str(reqs) + " does not equal expected result " + str(values["expected"][reqs]))
            values["tests"][reqs]["fail"] = 1
    else:
        print("No response was found for test " + str(reqs) + ", skipping")

# Check the request times and see if any exceeded the maximum set in maxRequest
for reqs in values["elapsed"].keys():
    if values["elapsed"][reqs] > maxRequest:
        print("Error: API request " + str(reqs) + " took longer than maximum duration " + str(maxRequest) + ". Failing test")
        values["tests"][reqs]["fail"] = 1

# Check the getConsumptionOffsets output of each test
#  Test 2

if not values["tests"]["addConAmpsFirst"].get("fail", 0):
    values["tests"]["addConAmpsFirst"]["fail"] = 1
    for offsets in values["status"]["AmpsFirst"].keys():
        if offsets == "First Amp Offset Positive":
            if values["status"]["AmpsFirst"][offsets]["value"] == values["target"]["ampsFirst"]:
                if values["status"]["AmpsFirst"][offsets]["unit"] == "A":
                    values["tests"]["addConAmpsFirst"]["fail"] = 0

#  Test 3
if not values["tests"]["addConAmpsSecond"].get("fail", 0):
    values["tests"]["addConAmpsSecond"]["fail"] = 1
    for offsets in values["status"]["AmpsSecond"].keys():
        if offsets == "Second Amp Offset Negative":
            if values["status"]["AmpsSecond"][offsets]["value"] == values["target"]["ampsSecond"]:
                if values["status"]["AmpsSecond"][offsets]["unit"] == "A":
                    values["tests"]["addConAmpsSecond"]["fail"] = 0

#  Test 4
if not values["tests"]["addConWattsFirst"].get("fail", 0):
    values["tests"]["addConWattsFirst"]["fail"] = 1
    for offsets in values["status"]["WattsFirst"].keys():
        if offsets == "First Watt Offset Positive":
            if values["status"]["WattsFirst"][offsets]["value"] == values["target"]["wattsFirst"]:
                if values["status"]["WattsFirst"][offsets]["unit"] == "W":
                    values["tests"]["addConWattsFirst"]["fail"] = 0

# Test 5
if not values["tests"]["addConWattsSecond"].get("fail", 0):
    values["tests"]["addConWattsSecond"]["fail"] = 1
    for offsets in values["status"]["WattsSecond"].keys():
        if offsets == "Second Watts Offset Negative":
            if values["status"]["WattsSecond"][offsets]["value"] == values["target"]["wattsSecond"]:
                if values["status"]["WattsSecond"][offsets]["unit"] == "W":
                    values["tests"]["addConWattsSecond"]["fail"] = 0


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
