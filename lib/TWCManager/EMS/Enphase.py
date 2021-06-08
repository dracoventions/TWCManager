# Enphase Monitoring Portal Integration
import logging
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class Enphase:

    import requests

    apiKey = None
    # cacheTime is a bit higher than local EMS modules
    # because we're polling an external API
    cacheTime = 60
    config = None
    configConfig = None
    configEnphase = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    status = False
    systemID = None
    timeout = 10
    userID = None
    voltage = 0

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configEnphase = master.config["sources"]["Enphase"]
        except KeyError:
            self.configEnphase = {}
        self.apiKey = self.configEnphase.get("apiKey", None)
        self.serverIP = self.configEnphase.get("serverIP", None)
        self.serverPort = self.configEnphase.get("serverPort", 80)
        self.status = self.configEnphase.get("enabled", False)
        self.systemID = self.configEnphase.get("systemID", None)
        self.userID = self.configEnphase.get("userID", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (
            ((not self.systemID) or (not self.apiKey) or (not self.userID))
            and ((not self.serverIP) or (not self.serverPort))
        ):
            self.master.releaseModule("lib.TWCManager.EMS", "Enphase")
            return None

        # Drop the cacheTime to 10 seconds if we use the local API
        if self.serverIP and self.serverPort:
            self.cacheTime = 10

    def getConsumption(self):

        if not self.status:
            logger.debug("Enphase EMS Module Disabled. Skipping getConsumption")
            return None

        # Perform updates if necessary
        self.update()

        # Return current consumption value
        return float(self.consumedW)

    def getGeneration(self):

        if not self.status:
            logger.debug("Enphase EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getPortalData(self):
        # Determine if this is a Cloud API or Local API query
        url = ""

        if self.apiKey and self.userID and self.systemID:
            url = "https://api.enphaseenergy.com/api/v2/systems/" + self.systemID
            url += "/summary?key=" + self.apiKey + "&user_id=" + self.userID
        elif self.serverIP and self.serverPort:
            url = "http://" + self.serverIP + ":" + str(self.serverPort)
            url += "/production.json?details=1&classic-1"

        return self.getPortalValue(url)

    def getPortalValue(self, url):

        # Fetch the specified URL from the Enphase Portal and return the data
        self.fetchFailed = False

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to Enphase Portal to fetch sensor value",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            logger.log(
                logging.INFO4,
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to Enphase Portal to fetch sensor value",
            )
            return ""
        else:
            return r.json()

    def update(self):

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            portalData = self.getPortalData()
            if portalData:
                try:
                    # Determine if this is Local or Cloud API
                    if self.apiKey and self.userID and self.systemID:
                        self.generatedW = int(portalData["current_power"])
                    elif self.serverIP and self.serverPort:
                        self.generatedW = int(portalData["production"][1]["wNow"])
                        self.consumedW = int(portalData["consumption"][0]["wNow"])
                        self.voltage = int(portalData["consumption"][0]["rmsVoltage"])
                except (KeyError, TypeError) as e:
                    logger.log(
                        logging.INFO4,
                        "Exception during parsing Enphase data (current_power)",
                    )
                    logger.debug(e)
            else:
                logger.log(
                    logging.INFO4, "Enphase API result does not contain json content."
                )
                self.fetchFailed = True

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
