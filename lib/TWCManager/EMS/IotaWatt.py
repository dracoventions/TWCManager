import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class IotaWatt:

    # IotaWatt EMS Module
    # Fetches Consumption and Generation details from IotaWatt

    import requests
    import time

    apiKey = None
    cacheTime = 10
    config = None
    configConfig = None
    configIotaWatt = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    iotaWattOutputConsumption = None
    iotaWattOutputGeneration = None
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    timeout = 2

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configIotaWatt = master.config["sources"]["IotaWatt"]
        except KeyError:
            self.configIotaWatt = {}
        self.status = self.configIotaWatt.get("enabled", False)
        self.serverIP = self.configIotaWatt.get("serverIP", None)
        self.iotaWattOutputConsumption = self.configIotaWatt.get(
            "outputConsumption", None
        )
        self.iotaWattOutputGeneration = self.configIotaWatt.get(
            "outputGeneration", None
        )

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP):
            self.master.releaseModule("lib.TWCManager.EMS", "IotaWatt")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            logger.debug("Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getAPIValue(self, output):
        url = "http://" + self.serverIP + "/status?outputs"
        headers = {
            "content-type": "application/json",
        }

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching IotaWatt EMS output value " + str(output))
            httpResponse = self.requests.get(url, headers=headers, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to IotaWatt to fetch output values",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4,
                "Read Timeout occurred fetching IotaWatt sensor value",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        jsonResponse = (
            httpResponse.json()
            if httpResponse and httpResponse.status_code == 200
            else None
        )

        if jsonResponse:
            for item in jsonResponse["outputs"]:
                if item["name"] == output:
                    return item["value"]
        else:
            return None

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from IotaWatt.

            if self.iotaWattOutputConsumption:
                apivalue = self.getAPIValue(self.iotaWattOutputConsumption)
                if self.fetchFailed is not True:
                    logger.debug("getConsumption returns " + str(apivalue))
                    self.consumedW = float(apivalue)
                else:
                    logger.debug("getConsumption fetch failed, using cached values")
            else:
                logger.debug("Consumption Entity Not Supplied. Not Querying")

            if self.iotaWattOutputGeneration:
                apivalue = self.getAPIValue(self.iotaWattOutputGeneration)
                if self.fetchFailed is not True:
                    logger.debug("getGeneration returns " + str(apivalue))
                    self.generatedW = float(apivalue)
                else:
                    logger.debug("getGeneration fetch failed, using cached values")
            else:
                logger.debug("Generation Entity Not Supplied. Not Querying")

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
