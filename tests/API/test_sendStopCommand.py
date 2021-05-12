#!/usr/bin/env python3

import json
import requests

# Configuration
skipFailure = 0

# Disable environment import to avoid proxying requests
session = requests.Session()
session.trust_env = False

success = 1
response = None

try:
    response = session.post("http://127.0.0.1:8088/api/sendStopCommand", timeout=30)
except requests.Timeout:
    print("Error: Connection Timed Out")
    success = 0
except requests.ConnectionError:
    print("Error: Connection Error")
    success = 0

if response.status_code == 204:
    success = 1
else:
    print("Error: Response code " + str(response.status_code))
    success = 0

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
