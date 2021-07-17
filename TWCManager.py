#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/lib")
try:
   sys.path.remove(os.path.dirname(os.path.realpath(__file__)))
except ValueError:
    # Current directory is not in path. Show current path
    print("It appears you may have a different setup - if you get an error that TWCManager is not a package, please paste this output into a GitHub issue:")
    print("Current Path:" + os.path.realpath(__file__))
    print("Python Path:" + sys.path)
    #pass

import TWCManager.TWCManager
