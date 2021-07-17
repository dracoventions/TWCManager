#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/lib")
sys.path.remove(os.path.dirname(os.path.realpath(__file__)))

import TWCManager.TWCManager
