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
HOSTNAME="`hostname -s`"
FILEUNIQUE="`basename $FILE`.${HOSTNAME}.`date +%s`"
SERVER=172.17.0.1
TOKEN=0baa9000ff4ab70a6f9f89733438767a

curl -X PUT -Ffile=$FILE "http://${SERVER}:25478/${FILEUNIQUE}?token=${TOKEN}"
