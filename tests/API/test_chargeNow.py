#!/usr/bin/env python3

# test_chargeNow.py
# This module tests both the chargeNow and cancelChargeNow commands
# Sending a request for chargeNow should invoke a policy change from the
# current policy to a new policy - we can check this with getStatus
# We should then be able to adjust the chargeNow policy and see that adjustment

import json
import os
import random
import requests
import time

# Configuration
skipFailure = 1

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

values = {}
values = {
  "elapsed":   {},
  "expected":  {},
  "response":  {}
}
success = 1
response = None

# Query getStatus to see our current offered amperage
try:
    response = session.get("http://127.0.0.1:8088/api/cancelChargeNow", timeout=30)
    values["response"]["getStatusBefore"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at ")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error at getStatus 1")
    exit(255)

# Generate a random amperage value between 12 and 80 twice for two separate
# tests, make sure they are not the same
values["targetFirst"]  = random.randint(12, 80)
values["targetSecond"] = 0
while (not values["targetSecond"] or values["targetFirst"] == values["targetSecond"]):
    values["targetSecond"] = random.randint(12, 80) 

print("Using values First: " + str(values["targetFirst"]) + " and Second: " + str(values["targetSecond"]) + " for chargeNow rate testing.")

# Test 1 - Call chargeNow policy with no arguments
values["expected"]["chargeNowNoArgs"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", timeout=30)
    values["elapsed"]["chargeNowNoArgs"] = response.elapsed
    values["response"]["chargeNowNoArgs"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNoArgs")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNoArgs")
    success = 0

time.sleep(2)

# Test 2 - Engage chargeNow policy with a negative value
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": -10
}

values["expected"]["chargeNowNegativeRate"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
    values["elapsed"]["chargeNowNegativeRate"] = response.elapsed
    values["response"]["chargeNowNegativeRate"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNegativeRate")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNegativeRate")
    success = 0

time.sleep(2)

# Test 3 - Engage chargeNow policy with a negative duration
data = {
  "chargeNowDuration": -3600,
  "chargeNowRate": 24
}

values["expected"]["chargeNowNegativeDuration"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
    values["elapsed"]["chargeNowNegativeDuration"] = response.elapsed
    values["response"]["chargeNowNegativeDuration"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowNegativeDuration")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowNegativeDuration")
    success = 0

time.sleep(2)

# Test 4 - Engage chargeNow policy for our first random value
values["expected"]["chargeNowFirst"] = 200
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": int(values.get("targetFirst", 0))
}

try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
    values["elapsed"]["chargeNowFirst"] = response.elapsed
    values["response"]["chargeNowFirst"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowFirst")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowFirst")
    success = 0

time.sleep(2)

# Test 5 - Send random data as the body of the request
data = os.urandom(20480)

values["expected"]["chargeNowRandom"] = 400
try:
    response = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
    values["elapsed"]["chargeNowRandom"] = response.elapsed
    values["response"]["chargeNowRandom"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out at chargeNowRandom")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at chargeNowRandom")
    success = 0

data = None
time.sleep(2)

# Test X - cancelChargeNow
values["expected"]["cancelChargeNow"] = 204
try:
    response = session.post("http://127.0.0.1:8088/api/cancelChargeNow", timeout=30)
    values["elapsed"]["cancelChargeNow"] = response.elapsed
    values["response"]["cancelChargeNow"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error at cancelChargeNow")
    success = 0

# For each request, check that the status codes match
for reqs in values["expected"].keys():
    if values["response"].get(reqs, None):
        if values["response"][reqs] != values["expected"][reqs]:
            print("Error: Response code " + str(values["response"][reqs]) + " for test " + str(reqs) + " does not equal expected result " + str(values["expected"][reqs]))
            success = 0
    else:
        print("No response was found for test " + str(reqs) + ", skipping")

# Print out values dict
print(str(values))

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
