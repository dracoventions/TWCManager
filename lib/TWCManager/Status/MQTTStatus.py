# MQTT Status Output
# Publishes the provided key and value pair to the provided topic prefix

from termcolor import colored
from ww import f


class MQTTStatus:

    import time
    import paho.mqtt.client as mqtt

    brokerIP = None
    brokerPort = 1883
    config = None
    configConfig = None
    configMQTT = {}
    connectionState = 0
    debugLevel = 0
    master = None
    msgQueue = []
    msgQueueBuffer = []
    msgQueueMax = 16
    msgRate = {}
    msgRatePerTopic = 60
    password = None
    status = False
    serverTLS = False
    topicPrefix = None
    username = None

    def __init__(self, master):
        self.config = master.config
        self.master = master
        try:
            self.configConfig = self.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configMQTT = self.config["status"]["MQTT"]
        except KeyError:
            self.configMQTT = {}
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configMQTT.get("enabled", False)
        self.brokerIP = self.configMQTT.get("brokerIP", None)
        self.topicPrefix = self.configMQTT.get("topicPrefix", None)
        self.username = self.configMQTT.get("username", None)
        self.password = self.configMQTT.get("password", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.brokerIP):
            self.master.releaseModule("lib.TWCManager.Status", "MQTTStatus")

    def setStatus(self, twcid, key_underscore, key_camelcase, value, unit):
        if self.status:

            # Format TWCID nicely
            twident = None
            if len(twcid) == 2:
                twident = "%02X%02X" % (twcid[0], twcid[1])
            else:
                twident = str(twcid.decode("utf-8"))
            topic = self.topicPrefix + "/" + twident
            topic = topic + "/" + key_camelcase

            # Perform rate limiting first (as there are some very chatty topics).
            # For each message that comes through, we take the topic name and check
            # when we last sent a message. If it was less than msgRatePerTopic
            # seconds ago, we dampen it.
            if topic in self.msgRate:
                if (self.time.time() - self.msgRate[topic]) < self.msgRatePerTopic:
                    return True
                else:
                    self.msgRate[topic] = self.time.time()
            else:
                self.msgRate[topic] = self.time.time()

            # Now, we push the message that we'd like to send into the
            # list of messages to be published once a connection is established
            msg = {"topic": topic, "payload": value}
            self.msgQueue.append(msg.copy())

            # If msgQueue size exceeds msgQueueMax, trim the list size
            # This will discard MQTT messages in environments where the MQTT
            # broker cannot accept the rate of MQTT messages sent
            if len(self.msgQueue) > (self.msgQueueMax + 8):
                del self.msgQueue[: self.msgQueueMax]

            # Now, we attempt to establish a connection to the MQTT broker
            if self.connectionState == 0:
                self.master.debugLog(
                    10, "MQTTStatus", "MQTT Status: Attempting to Connect"
                )
                try:
                    client = self.mqtt.Client()
                    if self.username and self.password:
                        client.username_pw_set(self.username, self.password)
                    client.on_connect = self.mqttConnected
                    client.connect_async(
                        self.brokerIP, port=self.brokerPort, keepalive=30
                    )
                    self.connectionState = 1
                    client.loop_start()
                except ConnectionRefusedError as e:
                    self.master.debugLog(
                        4,
                        "MQTTStatus",
                        "Error connecting to MQTT Broker to publish topic values",
                    )
                    self.master.debugLog(10, "MQTTStatus", str(e))
                    return False
                except OSError as e:
                    self.master.debugLog(
                        4,
                        "MQTTStatus",
                        "Error connecting to MQTT Broker to publish topic values",
                    )
                    self.master.debugLog(10, "MQTTStatus", str(e))
                    return False

    def mqttConnected(self, client, userdata, flags, rc):
        # This callback function is called once the MQTT client successfully
        # connects to the MQTT server. It will then publish all queued messages
        # to the server, and then disconnect.

        self.master.debugLog(
            10, "MQTTStatus", "Connected to MQTT Broker with RC: " + str(rc)
        )
        self.master.debugLog(11, "MQTTStatus", "Copy Message Buffer")
        self.msgQueueBuffer = self.msgQueue.copy()
        self.master.debugLog(11, "MQTTStatus", "Clear Message Buffer")
        self.msgQueue.clear()

        for msg in self.msgQueueBuffer:
            self.master.debugLog(
                8,
                "MQTTStatus",
                "Publishing MQTT Topic "
                + str(msg["topic"])
                + " (value is "
                + str(msg["payload"])
                + ")",
            )
            try:
                pub = client.publish(msg["topic"], payload=msg["payload"], qos=0)
            except e:
                self.master.debugLog(
                    4, "MQTTStatus", "Error publishing MQTT Topic Status"
                )
                self.master.debugLog(10, "MQTTStatus", str(e))

        client.loop_stop()
        self.msgQueueBuffer.clear()
        self.connectionState = 0
        client.disconnect()
