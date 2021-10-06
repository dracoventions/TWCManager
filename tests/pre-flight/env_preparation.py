#!/usr/bin/env python3

from grp import getgrnam
from pwd import getpwnam
import os
import subprocess

#print("Create files")
gid = getgrnam('twcmanager').gr_gid
uid = getpwnam('twcmanager').pw_uid
os.makedirs("/etc/twcmanager/csv", exist_ok=True)
os.chown("/etc/twcmanager/csv", uid, gid)

os.makedirs("/etc/twcmanager/log", exist_ok=True)
os.chown("/etc/twcmanager/log", uid, gid)

sqlite = "/etc/twcmanager/twcmanager.sqlite"
fhandle = open(sqlite, "a")
try:
    os.utime(sqlite, None)
finally:
    fhandle.close()
os.chown(sqlite, uid, gid)
os.chmod(sqlite, 0o664)

#print("Stopping mosquitto...")
devnull = open(os.devnull, 'w')
subprocess.call(["service", "mosquitto", "stop"], stdout=devnull, stderr=devnull)

mospwd = open("/etc/mosquitto/passwd", "w+")
mospwd.write("twcmanager:twcmanager")
mospwd.close()

#print("Converting mosquitto password file")
subprocess.call(["mosquitto_passwd", "-U", "/etc/mosquitto/passwd"])

#print("Starting mosquitto...")
subprocess.call(["service", "mosquitto", "start"], stdout=devnull, stderr=devnull)
