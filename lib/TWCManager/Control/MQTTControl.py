import logging

logger = logging.getLogger("\U0001F3AE MQTT")


class MQTTControl:

    import paho.mqtt.client as mqtt
    import _thread

    brokerIP = None
    brokerPort = 1883
    __client = None
    config = None
    configConfig = None
    configMQTT = None
    connectionState = 0
    master = None
    password = None
    status = False
    serverTLS = False
    topicPrefix = None
    username = None

    def __init__(self, master):
        self.config = master.config
        try:
            self.configConfig = self.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configMQTT = self.config["control"]["MQTT"]
        except KeyError:
            self.configMQTT = {}
        self.status = self.configMQTT.get("enabled", False)
        self.brokerIP = self.configMQTT.get("brokerIP", None)
        self.master = master
        self.topicPrefix = self.configMQTT.get("topicPrefix", None)
        self.username = self.configMQTT.get("username", None)
        self.password = self.configMQTT.get("password", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.brokerIP):
            self.master.releaseModule("lib.TWCManager.Control", "MQTTControl")
            return None

        if self.status:
            # Subscribe to the specified topic prefix, and process incoming messages
            # to determine if they represent control messages
            logger.debug("Attempting to Connect")
            if self.brokerIP:
                self.__client = self.mqtt.Client("MQTTCtrl")
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

                self.connectionState = 1
                self.__client.loop_start()

            else:
                logger.log(logging.INFO4, "Module enabled but no brokerIP specified.")

    def mqttConnect(self, client, userdata, flags, rc):
        logger.log(logging.INFO5, "MQTT Connected.")
        logger.log(logging.INFO5, "Subscribe to " + self.topicPrefix + "/#")
        res = self.__client.subscribe(self.topicPrefix + "/#", qos=0)
        logger.log(logging.INFO5, "Res: " + str(res))

    def mqttMessage(self, client, userdata, message):

        # Takes an MQTT message which has a message body of the following format:
        # [Amps to charge at],[Seconds to charge for]
        # eg. 24,3600
        if message.topic == self.topicPrefix + "/control/chargeNow":
            payload = str(message.payload.decode("utf-8"))
            logger.log(
                logging.INFO3, "MQTT Message called chargeNow with payload " + payload
            )
            plsplit = payload.split(",", 1)
            if len(plsplit) == 2:
                self.master.setChargeNowAmps(int(plsplit[0]))
                self.master.setChargeNowTimeEnd(int(plsplit[1]))
                self.master.getModuleByName("Policy").applyPolicyImmediately()
                self.master.queue_background_task({"cmd": "saveSettings"})
            else:
                logger.info(
                    "MQTT chargeNow command failed: Expecting comma seperated string in format amps,seconds"
                )

        if message.topic == self.topicPrefix + "/control/chargeNowEnd":
            logger.log(logging.INFO3, "MQTT Message called chargeNowEnd")
            self.master.resetChargeNowAmps()
            self.master.getModuleByName("Policy").applyPolicyImmediately()
            self.master.queue_background_task({"cmd": "saveSettings"})

        if message.topic == self.topicPrefix + "/control/stop":
            logger.log(logging.INFO3, "MQTT Message called Stop")
            self._thread.interrupt_main()

    def mqttSubscribe(self, client, userdata, mid, granted_qos):
        logger.info("Subscribe operation completed with mid " + str(mid))
