#!/usr/bin/env python3

# test_chargeNow.py
# This module tests both the chargeNow and cancelChargeNow commands
# Sending a request for chargeNow should invoke a policy change from the
# current policy to a new policy - we can check this with getStatus
# We should then be able to adjust the chargeNow policy and see that adjustment

import json
import random
import requests

# Configuration
skipFailure = 0

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

values = {}
success = 1
response = {}

# Query getStatus to see our current offered amperage
try:
    response["getStatusBefore"] = session.get("http://127.0.0.1:8088/api/cancelChargeNow", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

# Generate a random amperage value between 12 and 80 twice for two separate
# tests, make sure they are not the same
values["targetFirst"]  = random.randint(12, 80)
values["targetSecond"] = 0
while (not values["targetSecond"] or values["targetFirst"] == values["targetSecond"]):
    values["targetSecond"] = random.randint(12, 80) 

# Test 1 - Call chargeNow policy with no arguments
try:
    response["chargeNowNoArgs"] = session.post("http://127.0.0.1:8088/api/chargeNow", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

print(str(response["chargeNowNoArgs"]))

# Test 2 - Engage chargeNow policy with a negative value
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": -10
}

try:
    response["chargeNowNegativeRate"] = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

print(str(response["chargeNowNegativeRate"]))

# Test 3 - Engage chargeNow policy with a negative duration
data = {
  "chargeNowDuration": -3600,
  "chargeNowRate": 24
}

try:
    response["chargeNowNegativeDuration"] = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

print(str(response["chargeNowNegativeDuration"]))

# Test 4 - Engage chargeNow policy for our first random value
data = {
  "chargeNowDuration": 3600,
  "chargeNowRate": values["targetFirst"]
}

try:
    response["chargeNowFirst"] = session.post("http://127.0.0.1:8088/api/chargeNow", data=data, timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

print(str(response["chargeNowFirst"]))

# Test X - cancelChargeNow
try:
    response["cancelChargeNow"] = session.post("http://127.0.0.1:8088/api/cancelChargeNow", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    exit(255)
except requests.ConnectionError:
    print("Error: Connection Error")
    exit(255)

if response.status_code == 200:
    success = 1
else:
    print("Error: Response code " + str(response.status_code))
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
