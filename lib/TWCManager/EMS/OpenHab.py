class OpenHab:

    # OpenHab EMS Module
    # Fetches Consumption and Generation details from OpenHab

    import requests
    import time

    apiKey = None
    cacheTime = 10
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
            self.configOpenHab = master.config["sources"]["OpenHab"]
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

    def debugLog(self, minlevel, message):
        if self.debugLevel >= minlevel:
            print("debugLog: (" + str(minlevel) + ") " + message)

    def getConsumption(self):

        if not self.status:
            self.debugLog(10, "OpenHab EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            self.debugLog(10, "OpenHab EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getAPIValue(self, item):
        url = ("http://" + self.serverIP + ":" + str(self.serverPort) + "/rest/items/" + item + "/state")

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            self.debugLog(10, "Fetching OpenHab EMS sensor value " + str(item))
            httpResponse = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.debugLog(
                4, "Error connecting to OpenHab to publish sensor values"
            )
            self.debugLog(10, str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            self.debugLog(
                4, "Read Timeout occurred fetching OpenHab sensor value"
            )
            self.debugLog(10, str(e))
            self.fetchFailed = True
            return False

        response = httpResponse.text
        response = response.strip()

        # Strip units like '12.3 W'
        if " " in response:
            return response.split(" ")[0]
        return response

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from OpenHab sensor.

            if self.consumptionItem:
                apivalue = self.getAPIValue(self.consumptionItem)
                if self.fetchFailed is not True:
                    self.debugLog(10, "OpenHab getConsumption returns " + str(apivalue))
                    self.consumedW = float(apivalue)
                else:
                    self.debugLog(
                        10, "OpenHab getConsumption fetch failed, using cached values"
                    )
            else:
                self.debugLog(10, "OpenHab Consumption Entity Not Supplied. Not Querying")

            if self.generationItem:
                apivalue = self.getAPIValue(self.generationItem)
                if self.fetchFailed is not True:
                    self.debugLog(10, "OpenHab getGeneration returns " + str(apivalue))
                    self.generatedW = float(apivalue)
                else:
                    self.debugLog(
                        10, "OpenHab getGeneration fetch failed, using cached values"
                    )
            else:
                self.debugLog(10, "OpenHab Generation Entity Not Supplied. Not Querying")

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
