#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/lib")

# Remove any local local path references in sys.path, otherwise we'll
# see an error when we try to import TWCManager.TWCManager, as it will see
# us (TWCManager.py) instead of the package (lib/TWCManager) and fail.
if "" in sys.path:
    sys.path.remove("")

if "." in sys.path:
    sys.path.remove(".")

if os.path.dirname(os.path.realpath(__file__)) in sys.path:
    sys.path.remove(os.path.dirname(os.path.realpath(__file__)))

import TWCManager.TWCManager
