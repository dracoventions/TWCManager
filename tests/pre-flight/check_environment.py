#!/usr/bin/env python3

import os
import stat
from grp import getgrgid
from pwd import getpwuid

# check_environment.py
#
# This script will check that the install completed successfully.
# We'll check that the correct packages were installed, that /etc/twcmanager was created
# and that the permissions are correct

success = 1

def check_file(filename, exp_user, exp_group, exp_mode):
    global success

    if os.path.exists(filename):
        # Good. Check permissions
        if not getpwuid(os.stat(filename).st_uid).pw_name == exp_user:
           # Owner is wrong
           print("Wrong ownership for %s" % filename) 
           success = 0

        if not getgrgid(os.stat(filename).st_gid).gr_name == exp_group:
           # Group is wrong
           print("Wrong group ownership for %s" % filename)
           success = 0

        # Set expected mode for directory
        expmode = int(exp_mode, 8)
        if not stat.S_IMODE(os.stat(filename).st_mode) == expmode:
           # Directory permissions are wrong
           print("Wrong permissions for %s" % filename)
           success = 0

    else:
        # Uh oh, error
        print("Error: %s doesn't exist" % filename)
        success = 0

check_file("/etc/twcmanager", "twcmanager", "twcmanager", "755")
check_file("/etc/twcmanager/config.json", "twcmanager", "twcmanager", "755")

if success:
    print("All tests passed")
    exit(0)
else:
    print("At least one test failed")
    exit(255)
