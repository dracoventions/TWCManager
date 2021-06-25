#!/bin/bash

LISTEN=`ss -ntulw | grep LISTEN | grep -c 8088`

if [ $LISTEN -lt 1 ]; then
	echo Error: Port is not listening
	exit 255
else
	echo Test passed: API Port is listening
	exit 0
fi
