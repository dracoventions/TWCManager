import logging
import requests
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class URL:

    # URL EMS Module
    # Fetches Consumption and Generation details from URL

    apiKey = None
    cacheTime = 10  # in seconds
    config = None
    configConfig = None
    configURL = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    consumptionItem = None
    generationItem = None
    lastFetch = 0
    master = None
    status = False
    URL = None
    timeout = 2

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configURL = master.config["sources"]["URL"]
        except KeyError:
            self.configURL = {}
        self.status = self.configURL.get("enabled", False)
        self.URL = self.configURL.get("url", None)
        self.consumptionItem = self.configURL.get("consumptionItem", None)
        self.generationItem = self.configURL.get("generationItem", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.URL):
            self.master.releaseModule("lib.TWCManager.EMS", "URL")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("URL EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            logger.debug("URL EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getAPIValue(self, item):
        url = self.URL + "/" + item

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching URL EMS item value " + str(item))
            httpResponse = requests.get(url, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            logger.log(logging.INFO4, "Error connecting to URL to fetch item values")
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except requests.exceptions.ReadTimeout as e:
            logger.log(logging.INFO4, "Read Timeout occurred fetching URL item value")
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        response = httpResponse.text
        response = response.strip()

        # Strip units like '12.3 W'
        if " " in response:
            return response.split(" ")[0]

        try:
            responseAsFloat = float(response)
            return responseAsFloat
        except ValueError:
            logger.log(logging.INFO4, "Fetched value from URL item is not a number")
            logger.debug("Server response: " + str(response))
            self.fetchFailed = True
            return False

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from URL item.

            if self.consumptionItem:
                apivalue = self.getAPIValue(self.consumptionItem)
                if self.fetchFailed is not True:
                    logger.debug("URL getConsumption returns " + str(apivalue))
                    self.consumedW = apivalue
                else:
                    logger.debug("URL getConsumption fetch failed, using cached values")
            else:
                logger.debug("URL Consumption Entity Not Supplied. Not Querying")

            if self.generationItem:
                apivalue = self.getAPIValue(self.generationItem)
                if self.fetchFailed is not True:
                    logger.debug("URL getGeneration returns " + str(apivalue))
                    self.generatedW = apivalue
                else:
                    logger.debug("URL getGeneration fetch failed, using cached values")
            else:
                logger.debug("URL Generation Entity Not Supplied. Not Querying")

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
