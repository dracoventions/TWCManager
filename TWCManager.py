#!/usr/bin/env python3

import os
import grp
import pwd
import sys

# If we are being run as root, drop privileges to twcmanager user
# This avoids any potential permissions issues if it is run as root and settings.json is created as root
if os.getuid() == 0:
    user = "twcmanager"
    groups = [g.gr_gid for g in grp.getgrall() if user in g.gr_mem]

    _, _, uid, gid, gecos, root, shell = pwd.getpwnam(user)
    groups.append(gid)
    os.setgroups(groups)
    os.setgid(gid)
    os.setuid(uid)

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
