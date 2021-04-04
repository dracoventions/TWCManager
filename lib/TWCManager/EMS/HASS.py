import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class HASS:

    # HomeAssistant EMS Module
    # Fetches Consumption and Generation details from HomeAssistant

    import requests
    import time

    apiKey = None
    cacheTime = 10
    config = None
    configConfig = None
    configHASS = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    hassEntityConsumption = None
    hassEntityGeneration = None
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    serverPort = 8123
    useHttps = False
    timeout = 2

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configHASS = master.config["sources"]["HASS"]
        except KeyError:
            self.configHASS = {}
        self.status = self.configHASS.get("enabled", False)
        self.serverIP = self.configHASS.get("serverIP", None)
        self.serverPort = self.configHASS.get("serverPort", 8123)
        self.useHttps = self.configHASS.get("useHttps", False)
        self.apiKey = self.configHASS.get("apiKey", None)
        self.hassEntityConsumption = self.configHASS.get("hassEntityConsumption", None)
        self.hassEntityGeneration = self.configHASS.get("hassEntityGeneration", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "HASS")
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

    def getAPIValue(self, entity):
        http = "http://" if not (self.useHttps) else "https://"
        url = http + self.serverIP + ":" + self.serverPort + "/api/states/" + entity
        headers = {
            "Authorization": "Bearer " + self.apiKey,
            "content-type": "application/json",
        }

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching HomeAssistant EMS sensor value " + str(entity))
            httpResponse = self.requests.get(url, headers=headers, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to HomeAssistant to fetch sensor values",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4,
                "Read Timeout occurred fetching HomeAssistant sensor value",
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
            return jsonResponse["state"]
        else:
            return None

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from HomeAssistant sensor.

            if self.hassEntityConsumption:
                apivalue = self.getAPIValue(self.hassEntityConsumption)
                if self.fetchFailed is not True:
                    logger.debug("getConsumption returns " + str(apivalue))
                    self.consumedW = float(apivalue)
                else:
                    logger.debug("getConsumption fetch failed, using cached values")
            else:
                logger.debug("Consumption Entity Not Supplied. Not Querying")

            if self.hassEntityGeneration:
                apivalue = self.getAPIValue(self.hassEntityGeneration)
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
