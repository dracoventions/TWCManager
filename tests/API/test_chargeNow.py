#!/usr/bin/env python3

# test_chargeNow.py
# This module tests both the chargeNow and cancelChargeNow commands
# Sending a request for chargeNow should invoke a policy change from the
# current policy to a new policy - we can check this with getStatus
# We should then be able to adjust the chargeNow policy and see that adjustment

from base64 import b64encode
import datetime
import json
import os
import random
import requests
import time

# Configuration
skipFailure = 0
maxRequest = datetime.timedelta(seconds=2)

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

values = {
  "elapsed":   {},
  "expected":  {},
  "response":  {},
  "status":    {},
  "tests":     {},
  "text":      {}
}
response = None

def getStatus(tag):
    # Query getStatus to see our current offered amperage
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

values["status"]["Before"] = getStatus("getStatusBefore")

# Generate a random amperage value between 12 and 80 twice for two separate
# tests, make sure they are not the same
values["targetFirst"]  = random.randint(12, 80)
values["targetSecond"] = 0
while (not values["targetSecond"] or values["targetFirst"] == values["targetSecond"]):
    values["targetSecond"] = random.randint(12, 80) 

print("Using values First: " + str(values["targetFirst"]) + " and Second: " + str(values["targetSecond"]) + " for chargeNow rate testing.")

# Test 1 - Call chargeNow policy with no arguments
values["expected"]["chargeNowNoArgs"] = 400
values["tests"]["chargeNowNoArgs"] = {}
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", timeout=30)
    values["elapsed"]["chargeNowNoArgs"] = response.elapsed
    values["response"]["chargeNowNoArgs"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNoArgs")
    values["tests"]["chargeNowNoArgs"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNoArgs")
    values["tests"]["chargeNowNoArgs"]["fail"] = 1

time.sleep(2)

# Test 2 - Engage chargeNow policy with a negative value
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": -10
}

values["tests"]["chargeNowNegativeRate"] = {}
values["expected"]["chargeNowNegativeRate"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", json=data, timeout=30)
    values["elapsed"]["chargeNowNegativeRate"] = response.elapsed
    values["response"]["chargeNowNegativeRate"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNegativeRate")
    values["tests"]["chargeNowNegativeRate"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNegativeRate")
    values["tests"]["chargeNowNegativeRate"]["fail"] = 1

time.sleep(2)

# Test 3 - Engage chargeNow policy with a negative duration
data = {
  "chargeNowDuration": -3600,
  "chargeNowRate": 24
}

values["tests"]["chargeNowNegativeDuration"] = {}
values["expected"]["chargeNowNegativeDuration"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", json=data, timeout=30)
    values["elapsed"]["chargeNowNegativeDuration"] = response.elapsed
    values["response"]["chargeNowNegativeDuration"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNegativeDuration")
    values["tests"]["chargeNowNegativeDuration"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNegativeDuration")
    values["tests"]["chargeNowNegativeDuration"]["fail"] = 1

time.sleep(2)

# Test 4 - Engage chargeNow policy for our first random value
values["tests"]["chargeNowFirst"] = {}
values["expected"]["chargeNowFirst"] = 204
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": int(values.get("targetFirst", 0))
}

try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", json=data, timeout=30)
    values["elapsed"]["chargeNowFirst"] = response.elapsed
    values["response"]["chargeNowFirst"] = response.status_code
    values["text"]["chargeNowFirst"] = response.text
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowFirst")
    values["tests"]["chargeNowFirst"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowFirst")
    values["tests"]["chargeNowFirst"]["fail"] = 1

time.sleep(2)
values["status"]["First"] = getStatus("getStatusFirst")
time.sleep(2)

# Test 5 - Send random data as the body of the request
data = os.urandom(20480)
data_ascii = { "text": b64encode(data).decode('utf-8') }

values["tests"]["chargeNowRandom"] = {}
values["expected"]["chargeNowRandom"] = 400

try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", json=data_ascii, timeout=30)
    values["elapsed"]["chargeNowRandom"] = response.elapsed
    values["response"]["chargeNowRandom"] = response.status_code
except TypeError:
    print("Data was unable to be serialized into JSON. Error with test.")
    values["tests"]["chargeNowRandom"]["fail"] = 1
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowRandom")
    values["tests"]["chargeNowRandom"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowRandom")
    values["tests"]["chargeNowRandom"]["fail"] = 1

data = None
data_ascii = None
time.sleep(2)

# Test 6 - Engage chargeNow policy for our second random value
values["tests"]["chargeNowSecond"] = {}
values["expected"]["chargeNowSecond"] = 204
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": int(values.get("targetSecond", 0))
}

try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", json=data, timeout=30)
    values["elapsed"]["chargeNowSecond"] = response.elapsed
    values["response"]["chargeNowSecond"] = response.status_code
    values["text"]["chargeNowSecond"] = response.text
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowSecond")
    values["tests"]["chargeNowSecond"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowSecond")
    values["tests"]["chargeNowSecond"]["fail"] = 1

values["status"]["Second"] = getStatus("getStatusSecond")
time.sleep(2)

# Test 7 - Send cancelChargeNow
values["tests"]["cancelChargeNow"] = {}
values["expected"]["cancelChargeNow"] = 204
try:
    response = session.post("http://127.0.0.1:8088/api/cancelChargeNow", timeout=30)
    values["elapsed"]["cancelChargeNow"] = response.elapsed
    values["response"]["cancelChargeNow"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out")
    values["tests"]["cancelChargeNow"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error at cancelChargeNow")
    values["tests"]["cancelChargeNow"]["fail"] = 1

values["status"]["Cancel"] = getStatus("getStatusCancel")

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

# Check that the two values that we selected are reflected in their status output
if (int(values["targetFirst"]) != float(values["status"]["First"]["maxAmpsToDivideAmongSlaves"])):
    print("Error: maxAmpsToDivideAmongSlaves doesn't match target for first chargeNow test")
    values["tests"]["chargeNowFirst"]["fail"] = 1

if (int(values["targetSecond"]) != float(values["status"]["Second"]["maxAmpsToDivideAmongSlaves"])):
    print("Error: maxAmpsToDivideAmongSlaves doesn't match target for second chargeNow test")
    values["tests"]["chargeNowSecond"]["fail"] = 1

 
# Print out values dict
#f = open("/tmp/twcmanager-tests/chargeNow.json", "a")
#f.write(str(values))
#f.close()

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
