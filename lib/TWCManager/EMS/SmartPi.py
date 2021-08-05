import logging
import requests
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SmartPi:

    # SmartPi EMS Module
    # Fetches Consumption and Generation details from SmartPi API

    cacheTime = 10
    config = None
    configConfig = None
    configSmartPi = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    lastFetch = 0
    master = None
    serverIP = None
    serverPort = 80
    showConsumption = False
    status = False
    timeout = 2

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = master.config.get("config", {})
        self.configSmartPi = master.config["sources"].get("SmartPi", {})
        self.serverIP = self.configSmartPi.get("serverIP", None)
        self.serverPort = self.configSmartPi.get("serverPort", 80)
        self.showConsumption = self.configSmartPi.get("showConsumption", False)
        self.status = self.configSmartPi.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP):
            self.master.releaseModule("lib.TWCManager.EMS", self.__class__.__name__)
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getConsumption")
            return 0

        # While we don't have separate generation or consumption values, if
        # the value is a positive value we report it as consumption
        if self.consumedW and self.showConsumption:
            return self.consumedW
        else:
            return 0

    def getGeneration(self):

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        if self.generatedW > 0:
            return self.generatedW
        else:
            return 0

    def getGenerationValues(self):
        url = "http://" + self.serverIP + ":" + self.serverPort + "/api/all/power/now"
        headers = {"content-type": "application/json"}

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching SmartPi EMS sensor values")
            httpResponse = requests.get(url, headers=headers, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4, "Error connecting to SmartPi to fetch sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4, "Read Timeout occurred fetching SmartPi sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        if httpResponse.status_code != 200:
            logger.log(
                logging.INFO4,
                "SmartPi API reports HTTP Status Code " + str(httpResponse.status_code),
            )
            return False

        if not httpResponse:
            logger.log(logging.INFO4, "Empty HTTP Response from SmartPi API")
            return False

        if httpResponse.json():
            genWatts = 0
            conWatts = 0
            try:
                for phase in httpResponse.json()["datasets"][0]["phases"]:
                    logger.log(
                        logging.INFO8,
                        "Logged "
                        + str(phase["values"][0]["data"])
                        + " "
                        + str(phase["values"][0]["unity"])
                        + " for phase "
                        + str(phase["name"]),
                    )
                    if float(phase["values"][0]["data"]) < 0:
                        genWatts += float(phase["values"][0]["data"])
                    else:
                        conWatts += float(phase["values"][0]["data"])
            except KeyError:
                logger.log(
                    logging.INFO4,
                    "Expected Key datasets[0][phases] not found in response from SmartPi API.",
                )

            self.generatedW = genWatts * -1
            self.consumedW = conWatts
        else:
            logger.log(logging.INFO4, "No JSON response from SmartPi API")

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from SmartPi.
            self.getGenerationValues()

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
