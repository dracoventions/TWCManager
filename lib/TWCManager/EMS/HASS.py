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
    debugLevel = 0
    fetchFailed = False
    generatedW = 0
    hassEntityConsumption = None
    hassEntityGeneration = None
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    serverPort = 8123
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
        self.apiKey = self.configHASS.get("apiKey", None)
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.hassEntityConsumption = self.configHASS.get("hassEntityConsumption", None)
        self.hassEntityGeneration = self.configHASS.get("hassEntityGeneration", None)

        # Unload if this module is disabled or misconfigured
        if ((not self.status) or (not self.serverIP)
            or (int(self.serverPort) < 1)):
            self.master.releaseModule("lib.TWCManager.EMS","HASS");
            return None

    def debugLog(self, minlevel, message):
        if self.debugLevel >= minlevel:
            print("debugLog: (" + str(minlevel) + ") " + message)

    def getConsumption(self):

        if not self.status:
            self.debugLog(10, "HASS EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):

        if not self.status:
            self.debugLog(10, "HASS EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getAPIValue(self, entity):
        url = (
            "http://" + self.serverIP + ":" + self.serverPort + "/api/states/" + entity
        )
        headers = {
            "Authorization": "Bearer " + self.apiKey,
            "content-type": "application/json",
        }

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            self.debugLog(10, "Fetching HomeAssistant EMS sensor value " + str(entity))
            httpResponse = self.requests.get(url, headers=headers, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.debugLog(
                4, "Error connecting to HomeAssistant to publish sensor values"
            )
            self.debugLog(10, str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            self.debugLog(
                4, "Read Timeout occurred fetching HomeAssistant sensor value"
            )
            self.debugLog(10, str(e))
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
                    self.debugLog(10, "HASS getConsumption returns " + str(apivalue))
                    self.consumedW = float(apivalue)
                else:
                    self.debugLog(
                        10, "HASS getConsumption fetch failed, using cached values"
                    )
            else:
                self.debugLog(10, "HASS Consumption Entity Not Supplied. Not Querying")

            if self.hassEntityGeneration:
                apivalue = self.getAPIValue(self.hassEntityGeneration)
                if self.fetchFailed is not True:
                    self.debugLog(10, "HASS getGeneration returns " + str(apivalue))
                    self.generatedW = float(apivalue)
                else:
                    self.debugLog(
                        10, "HASS getGeneration fetch failed, using cached values"
                    )
            else:
                self.debugLog(10, "HASS Generation Entity Not Supplied. Not Querying")

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
