import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class MQTT:

    # MQTT EMS Module
    # Subscribes to Consumption and Generation details from MQTT Publisher

    import paho.mqtt.client as mqtt
    import time

    __config = None
    __configConfig = None
    __configMQTT = None
    __connectionState = 0
    consumedW = 0
    generatedW = 0
    __topicConsumption = None
    __topicGeneration = None
    master = None
    status = False
    serverIP = None
    serverPort = 8123

    def __init__(self, master):
        self.master = master
        self.__config = master.config
        try:
            self.__configConfig = master.config["config"]
        except KeyError:
            self.__configConfig = {}
        try:
            self.__configMQTT = master.config["sources"]["MQTT"]
        except KeyError:
            self.__configMQTT = {}

        self.status = self.__configMQTT.get("enabled", False)
        self.brokerIP = self.__configMQTT.get("brokerIP", None)
        self.username = self.__configMQTT.get("username", None)
        self.password = self.__configMQTT.get("password", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.brokerIP):
            self.master.releaseModule("lib.TWCManager.EMS", "MQTT")
            return None

        self.__topicConsumption = self.__configMQTT.get("topicConsumption", None)
        self.__topicGeneration = self.__configMQTT.get("topicGeneration", None)

        logger.debug("Attempting to Connect to MQTT Broker")
        if self.brokerIP:
            self.__client = self.mqtt.Client("MQTT.EMS")
            if self.username and self.password:
                self.__client.username_pw_set(self.username, self.password)
            self.__client.on_connect = self.mqttConnect
            self.__client.on_message = self.mqttMessage
            self.__client.on_subscribe = self.mqttSubscribe
            try:
                self.__client.connect_async(
                    self.brokerIP, port=self.brokerPort, keepalive=30
                )
            except ConnectionRefusedError as e:
                logger.log(logging.INFO4, "Error connecting to MQTT Broker")
                logger.debug(str(e))
                return False
            except OSError as e:
                logger.log(logging.INFO4, "Error connecting to MQTT Broker")
                logger.debug(str(e))
                return False

            self.__connectionState = 1
            self.__client.loop_start()

        else:
            logger.log(logging.INFO4, "Module enabled but no brokerIP specified.")

    def mqttConnect(self, client, userdata, flags, rc):
        logger.log(logging.INFO5, "MQTT Connected.")

        if self.__topicConsumption:
            logger.log(logging.INFO5, "Subscribe to " + self.__topicConsumption)
            res = self.__client.subscribe(self.__topicConsumption, qos=0)
            logger.log(logging.INFO5, "Res: " + str(res))

        if self.__topicGeneration:
            logger.log(logging.INFO5, "Subscribe to " + self.__topicGeneration)
            res = self.__client.subscribe(self.__topicGeneration, qos=0)
            logger.log(logging.INFO5, "Res: " + str(res))

    def mqttMessage(self, client, userdata, message):

        # Takes an MQTT message, and update the associated Generation/Consumption value
        payload = str(message.payload.decode("utf-8"))

        if message.topic == self.__topicConsumption:
            self.consumedW = payload
            logger.log(logging.INFO3, "MQTT EMS Consumption Value updated")

        if message.topic == self.__topicGeneration:
            self.generatedW = payload
            logger.log(logging.INFO3, "MQTT EMS Generation Value updated")

    def mqttSubscribe(self, client, userdata, mid, granted_qos):
        logger.info("Subscribe operation completed with mid " + str(mid))

    def getConsumption(self):

        if not self.status:
            logger.debug("Module Disabled. Skipping getConsumption")
            return 0

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            logger.debug("Module Disabled. Skipping getGeneration")
            return 0

        # Return generation value
        return self.generatedW
