#!/bin/bash

# Entrypoint script for Docker image of TWCManager.
# We use this to prepare the configuration for the first time
if [ ! -e "/etc/twcmanager/config.json" ]; then
    cp /usr/src/TWCManager/etc/twcmanager/config.json /etc/twcmanager/config.json
    chown twcmanager:twcmanager /etc/twcmanager /etc/twcmanager/config.json
fi

# This will exec the CMD from your Dockerfile
exec "$@"
