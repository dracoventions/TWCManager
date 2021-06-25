import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SmartMe:

    # SmartMe EMS Module
    # Fetches Consumption and Generation details from SmartMe API

    import requests
    import time

    cacheTime = 10
    config = None
    configConfig = None
    configSmartMe = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    lastFetch = 0
    master = None
    password = None
    serialNumber = None
    session = None
    status = False
    timeout = 2
    username = None

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = master.config.get("config", {})
        self.configSmartMe = master.config["sources"].get("SmartMe", {})
        self.password = self.configSmartMe.get("password", "")
        self.status = self.configSmartMe.get("enabled", False)
        self.serialNumber = self.configSmartMe.get("serialNumber", None)
        self.username = self.configSmartMe.get("username", "")

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (
            not self.serialNumber or not self.username or not self.password
        ):
            self.master.releaseModule("lib.TWCManager.EMS", self.__class__.__name__)
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getConsumption")
            return 0

        # While we don't have separate generation or consumption values, if
        # the value is a positive value we report it as consumption
        if self.generatedW < 0:
            return self.generatedW * -1
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
        url = "https://smart-me.com/api/DeviceBySerial?serial=" + self.serialNumber
        headers = {"content-type": "application/json"}

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching SmartMe EMS sensor values")
            self.session = self.requests.Session()
            self.session.auth = (self.username, self.password)
            httpResponse = self.session.get(url, headers=headers, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4, "Error connecting to SmartMe to fetching sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4, "Read Timeout occurred fetching SmartMe sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        if httpResponse.status_code != 200:
            logger.log(
                logging.INFO4,
                "SmartMe API reports HTTP Status Code " + str(httpResponse.status_code),
            )
            return False

        if not httpResponse:
            logger.log(logging.INFO4, "Empty HTTP Response from SmartMe API")
            return False

        if httpResponse.json():
            self.generatedW = float(httpResponse.json()["ActivePower"]) * -1
            if httpResponse.json()["ActivePowerUnit"] == "kW":
                # Unit is kW, multiply by 1000 for W
                self.generatedW = self.generatedW * 1000
        else:
            logger.log(logging.INFO4, "No JSON response from SmartMe API")

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from SmartMe.
            self.getGenerationValues()

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
