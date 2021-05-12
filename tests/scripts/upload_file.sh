#!/bin/bash

################################
# upload_file.sh
#
# This is a helper script for CI/CD testing run within dedicated TWCManager
# test environments. It will upload a file to an upload server for analysis
# should any strange behaviour need to be further reviewed.
#
# This would not be of much use outside of the dedicated test environment
#

FILE="$1"

if [ "$FILE " == " " ]; then
    echo "No filename specified. Exiting."
    exit 0
fi

if [ ! -e "$FILE" ]; then
    echo "Specified file (${FILE}) doesn't exist. Exiting."
    exit 0
fi

HOSTNAME="`hostname -s`"
FILEUNIQUE="`basename ${FILE}`.${HOSTNAME}.`date +%s`"
SERVER=172.17.0.1
TOKEN=0baa9000ff4ab70a6f9f89733438767a

curl --proxy "" -X PUT -Ffile=@$FILE "http://${SERVER}:25478/files/${FILEUNIQUE}?token=${TOKEN}"
