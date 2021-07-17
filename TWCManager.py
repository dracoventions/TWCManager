#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/lib")
try:
   sys.path.remove(os.path.dirname(os.path.realpath(__file__)))
except ValueError:
    # Current directory is not in path - ignore
    pass

import TWCManager.TWCManager
