#!/usr/bin/env python3

import requests

# Configuration
skipFailure = 0

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

response = None

values = {
  "elapsed":   {},
  "expected":  {},
  "response":  {},
  "status":    {},
  "tests":     {},
  "text":      {}
}

# Test 1 - Set Home Latitude setting
data = {
    "setting": "x",
    "value": "x"
}

values["tests"]["setHomeLat"] = {}
try:
    response = session.post("http://127.0.0.1:8088/api/setSetting", json=data, timeout=5)
    values["elapsed"]["setHomeLat"] = response.elapsed
    values["response"]["setHomeLat"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out")
    values["tests"]["setHomeLat"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error")
    values["tests"]["setHomeLat"]["fail"] = 1

# Test 2 - Set Home Longitude setting
data = {
    "setting": "x",
    "value": "x"
}

values["tests"]["setHomeLon"] = {}
try:
    response = session.post("http://127.0.0.1:8088/api/setSetting", json=data, timeout=5)
    values["elapsed"]["setHomeLon"] = response.elapsed
    values["response"]["setHomeLon"] = response.status_code
except requests.Timeout:
    print("Error: Connection Timed Out")
    values["tests"]["setHomeLon"]["fail"] = 1
except requests.ConnectionError:
    print("Error: Connection Error")
    values["tests"]["setHomeLon"]["fail"] = 1

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

