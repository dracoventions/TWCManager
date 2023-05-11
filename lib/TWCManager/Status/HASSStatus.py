# HomeAssistant Status Output
# Publishes the provided sensor key and value pair to a HomeAssistant instance

import logging
import time


logger = logging.getLogger("\U0001F4CA HASS")


class HASSStatus:
    import threading
    import requests

    apiKey = None
    config = None
    configConfig = None
    configHASS = None
    master = None
    msgRateInSeconds = 60
    resendRateInSeconds = 3600
    retryRateInSeconds = 60
    msgQueue = {}
    status = False
    serverIP = None
    serverPort = 8123
    useHttps = False
    timeout = 2
    backgroundTasksLock = threading.Lock()
    backgroundTasksThread = None

    def __init__(self, master):
        self.config = master.config
        self.master = master
        try:
            self.configConfig = self.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configHASS = self.config["status"]["HASS"]
        except KeyError:
            self.configHASS = {}
        self.status = self.configHASS.get("enabled", False)
        self.serverIP = self.configHASS.get("serverIP", None)
        self.serverPort = self.configHASS.get("serverPort", 8123)
        self.useHttps = self.configHASS.get("useHttps", False)
        self.apiKey = self.configHASS.get("apiKey", None)
        self.msgRateInSeconds = self.configHASS.get("msgRateInSeconds", 60)
        self.resendRateInSeconds = self.configHASS.get("resendRateInSeconds", 3600)
        self.retryRateInSeconds = self.configHASS.get("retryRateInSeconds", 60)

        # Unload if this module is disabled or misconfigured
        if (
            (not self.status)
            or (not self.serverIP)
            or (int(self.serverPort) < 1)
            or (not self.apiKey)
        ):
            self.master.releaseModule("lib.TWCManager.Status", "HASSStatus")
        else:
            self.backgroundTasksThread = self.threading.Thread(
                target=self.background_task_thread, args=()
            )
            self.backgroundTasksThread.daemon = True
            self.backgroundTasksThread.start()

    def getTwident(self, twcid):
        # Format TWCID nicely
        if len(twcid) == 2:
            return "%02X%02X" % (twcid[0], twcid[1])
        else:
            return str(twcid.decode("utf-8"))

    def background_task_thread(self):
        while True:
            time.sleep(self.msgRateInSeconds)
            self.backgroundTasksLock.acquire()
            for msgKey in self.msgQueue:
                msg = self.msgQueue[msgKey]
                if msg.elapsingTime < time.time():
                    self.sendingStatusToHASS(msg)
            self.backgroundTasksLock.release()

    def getSensorName(self, twcid, key_underscore):
        return "sensor.twcmanager_" + str(self.getTwident(twcid)) + "_" + key_underscore

    def setStatus(self, twcid, key_underscore, key_camelcase, value, unit):
        self.backgroundTasksLock.acquire()
        sensor = self.getSensorName(twcid, key_underscore)
        if (sensor not in self.msgQueue) or (self.msgQueue[sensor].value != value):
            self.msgQueue[sensor] = HASSMessage(
                time.time(),
                sensor,
                twcid,
                key_underscore,
                key_camelcase,
                value,
                unit,
            )
        self.backgroundTasksLock.release()

    def sendingStatusToHASS(self, msg):
        http = "http://" if not (self.useHttps) else "https://"
        url = http + self.serverIP + ":" + self.serverPort
        url = url + "/api/states/" + msg.sensor
        headers = {
            "Authorization": "Bearer " + self.apiKey,
            "content-type": "application/json",
        }
        try:
            logger.log(
                logging.INFO8,
                f"Sending POST request to HomeAssistant for sensor {msg.sensor} (value {msg.value}).",
            )

            devclass = ""
            state_class = ""
            if msg.unit in ["W", "kW"]:
                devclass = "power"
            elif msg.unit in ["Wh", "kWh", "MWh"]:
                devclass = "energy"
                state_class = "total"
            elif msg.unit == "A":
                devclass = "current"
                state_class = "measurement"
            elif msg.unit == "V":
                devclass = "voltage"
                state_class = "measurement"

            if len(msg.unit) > 0:
                self.requests.post(
                    url,
                    json={
                        "state": msg.value,
                        "attributes": {
                            "unit_of_measurement": msg.unit,
                            "device_class": devclass,
                            "state_class": state_class,
                            "friendly_name": "TWC "
                            + str(self.getTwident(msg.twcid))
                            + " "
                            + msg.key_camelcase,
                        },
                    },
                    timeout=self.timeout,
                    headers=headers,
                )
            else:
                self.requests.post(
                    url,
                    json={
                        "state": msg.value,
                        "attributes": {
                            "friendly_name": "TWC "
                            + str(self.getTwident(msg.twcid))
                            + " "
                            + msg.key_camelcase
                        },
                    },
                    timeout=self.timeout,
                    headers=headers,
                )
            # Setting elapsing time to now + resendRateInSeconds
            self.msgQueue[msg.sensor].elapsingTime = (
                time.time() + self.resendRateInSeconds
            )
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to HomeAssistant to publish sensor values",
            )
            logger.debug(str(e))
            self.settingRetryRate(msg)
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4,
                "Error connecting to HomeAssistant to publish sensor values",
            )
            logger.debug(str(e))
            self.settingRetryRate(msg)
            return False
        except Exception as e:
            logger.log(
                logging.INFO4, "Error during publishing HomeAssistant sensor values"
            )
            logger.debug(str(e))
            self.settingRetryRate(msg)
            return False

    def settingRetryRate(self, msg):
        # Setting elapsing time to now + retryRateInSeconds
        self.msgQueue[msg.sensor].elapsingTime = time.time() + self.retryRateInSeconds


class HASSMessage:
    elapsingTime = 0
    sensor = ""
    twcid = ""
    key_underscore = ""
    key_camelcase = ""
    value = None
    unit = ""

    def __init__(
        self, elapsingTime, sensor, twcid, key_underscore, key_camelcase, value, unit
    ):
        self.elapsingTime = elapsingTime
        self.sensor = sensor
        self.twcid = twcid
        self.key_underscore = key_underscore
        self.key_camelcase = key_camelcase
        self.value = value
        self.unit = unit
