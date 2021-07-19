#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/lib")

# Remove any local local path references in sys.path, otherwise we'll
# see an error when we try to import TWCManager.TWCManager, as it will see
# us (TWCManager.py) instead of the package (lib/TWCManager) and fail.
if '' in sys.path:
    os.path.remove('')

if '.' in sys.path:
    os.path.remove('.')

try:
   sys.path.remove(os.path.dirname(os.path.realpath(__file__)))
except ValueError:
    # Current directory is not in path. Show current path
    print("It appears you may have a different setup - if you get an error that TWCManager is not a package, please paste this output into a GitHub issue:")
    print("Current Path:" + os.path.realpath(__file__))
    print("Python Path:" + str(sys.path))
    #pass

import TWCManager.TWCManager
