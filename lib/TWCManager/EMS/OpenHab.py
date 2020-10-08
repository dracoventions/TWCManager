class OpenHab:

    # OpenHab EMS Module
    # Fetches Consumption and Generation details from OpenHab

    import requests
    import time

    apiKey = None
    cacheTime = 10  # in seconds
    config = None
    configConfig = None
    configOpenHab = None
    consumedW = 0
    debugLevel = 0
    fetchFailed = False
    generatedW = 0
    consumptionItem = None
    generationItem = None
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    serverPort = 8080
    timeout = 2

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configOpenHab = master.config["sources"]["openHAB"]
        except KeyError:
            self.configOpenHab = {}
        self.status = self.configOpenHab.get("enabled", False)
        self.serverIP = self.configOpenHab.get("serverIP", None)
        self.serverPort = self.configOpenHab.get("serverPort", 8080)
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.consumptionItem = self.configOpenHab.get("consumptionItem", None)
        self.generationItem = self.configOpenHab.get("generationItem", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "OpenHab")
            return None

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(
                10, "OpenHab", "OpenHab EMS Module Disabled. Skipping getConsumption"
            )
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(
                10, "OpenHab", "OpenHab EMS Module Disabled. Skipping getGeneration"
            )
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getAPIValue(self, item):
        url = (
            "http://"
            + self.serverIP
            + ":"
            + str(self.serverPort)
            + "/rest/items/"
            + item
            + "/state"
        )

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            self.master.debugLog(
                10, "OpenHab", "Fetching OpenHab EMS item value " + str(item)
            )
            httpResponse = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(
                4, "OpenHab", "Error connecting to OpenHab to fetch item values"
            )
            self.master.debugLog(10, "OpenHab", str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            self.master.debugLog(
                4, "OpenHab", "Read Timeout occurred fetching OpenHab item value"
            )
            self.master.debugLog(10, "OpenHab", str(e))
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
            self.master.debugLog(
                4, "OpenHab", "Fetched value from OpenHab item is not a number"
            )
            self.master.debugLog(10, "OpenHab", "Server response: " + str(response))
            self.fetchFailed = True
            return False

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from OpenHab item.

            if self.consumptionItem:
                apivalue = self.getAPIValue(self.consumptionItem)
                if self.fetchFailed is not True:
                    self.master.debugLog(
                        10, "OpenHab", "OpenHab getConsumption returns " + str(apivalue)
                    )
                    self.consumedW = apivalue
                else:
                    self.master.debugLog(
                        10,
                        "OpenHab",
                        "OpenHab getConsumption fetch failed, using cached values",
                    )
            else:
                self.master.debugLog(
                    10,
                    "OpenHab",
                    "OpenHab Consumption Entity Not Supplied. Not Querying",
                )

            if self.generationItem:
                apivalue = self.getAPIValue(self.generationItem)
                if self.fetchFailed is not True:
                    self.master.debugLog(
                        10, "OpenHab", "OpenHab getGeneration returns " + str(apivalue)
                    )
                    self.generatedW = apivalue
                else:
                    self.master.debugLog(
                        10,
                        "OpenHab",
                        "OpenHab getGeneration fetch failed, using cached values",
                    )
            else:
                self.master.debugLog(
                    10,
                    "OpenHab",
                    "OpenHab Generation Entity Not Supplied. Not Querying",
                )

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
