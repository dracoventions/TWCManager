#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time

def mqttConnected(client, userdata, flags, rc):
    global test_state
    test_state = 1

connection_time = 0
test_duration = 0
test_duration_max = 120
test_state = 0

client = mqtt.Client("MQTT.EMS.Test")
client.username_pw_set("twcmanager", "twcmanager")
client.on_connect = mqttConnected

client.connect_async(
   "127.0.0.1", port=1883, keepalive=30
)

# Run this test for a maximum of test_duration_max or until the test has completed, whichever comes first
while (test_duration < test_duration_max):
    if test_state == 0:
        # Waiting on connection to the MQTT Broker
        connection_time = test_duration
    elif test_state == 1:
        # Connection Established. Update MQTT topic.
        client.publish("/test", "test", qos=0)
        test_state = 2
    test_duration += 1
    time.sleep(0.1)
