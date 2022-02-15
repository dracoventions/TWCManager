import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class EmonCMS:

    # OpenEnergyMonitor (EmonCMS) Module
    # Fetches Consumption and Generation details from Open Energy Monitor

    import requests
    import time

    apiKey = None
    cacheTime = 10
    config = None
    configConfig = None
    configEmonCMS = None
    consumedW = 0
    generatedW = 0
    consumptionFeed = None
    generationFeed = None
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    serverPort = 80
    serverPath = None
    useHttps = False
    timeout = 2
    entities = None

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configEmonCMS = master.config["sources"]["EmonCMS"]
        except KeyError:
            self.configEmonCMS = {}
        self.status = self.configEmonCMS.get("enabled", False)
        self.serverIP = self.configEmonCMS.get("serverIP", None)
        self.serverPort = self.configEmonCMS.get("serverPort", 80)
        self.serverPath = self.configEmonCMS.get("serverPath", "")
        self.useHttps = self.configEmonCMS.get("useHttps", False)
        self.apiKey = self.configEmonCMS.get("apiKey", None)
        self.consumptionFeed = self.configEmonCMS.get("consumptionFeed", None)
        self.generationFeed = self.configEmonCMS.get("generationFeed", None)
        self.entities = {}

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "EmonCMS")
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

    def getFeeds(self, feeds):
        if len(feeds) == 0:
            logger.log(
                logging.INFO4,
                "No EmonCMS feeds to fetch",
            )
            return False

        http = "http://" if not (self.useHttps) else "https://"
        url = (
            http
            + self.serverIP
            + ":"
            + self.serverPort
            + self.serverPath
            + "/feed/fetch.json?ids="
            + ",".join(feeds)
        )
        headers = {
            "Authorization": "Bearer " + self.apiKey,
        }

        try:
            logger.debug("Fetching EmonCMS feeds " + ",".join(feeds))
            httpResponse = self.requests.get(url, headers=headers, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to EmonCMS to fetch feed",
            )
            logger.debug(str(e))
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4,
                "Read Timeout fetching EmonCMS feed",
            )
            logger.debug(str(e))
            return False

        if httpResponse.status_code != 200:
            logger.log(
                logging.INFO4,
                "Failed to fetch "
                + url
                + " HTTP Status: "
                + str(httpResponse.status_code),
            )
            return False

        jsonResponse = (
            httpResponse.json()
            if httpResponse and httpResponse.status_code == 200
            else None
        )

        if jsonResponse:
            return jsonResponse
        else:
            return None

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from EmonCMS
            feeds = []

            if self.consumptionFeed:
                feeds.append(self.consumptionFeed)

            if self.consumptionFeed:
                feeds.append(self.generationFeed)

            vals = self.getFeeds(feeds)
            if vals:
                if self.consumptionFeed:
                    self.consumedW = float(vals.pop())
                    logger.debug("getConsumption returns " + str(self.consumedW))

                if self.generationFeed:
                    self.generatedW = float(vals.pop())
                    logger.debug("getGeneration returns " + str(self.generatedW))

                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
