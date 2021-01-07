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
    debugLevel = 0
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
        self.username = self.configSmartMe.get("password", "")
        self.debugLevel = self.configConfig.get("debugLevel", 0)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serialNumber or not self.username or not self.password):
            self.master.releaseModule("lib.TWCManager.EMS", "SmartMe")
            return None

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(10, "SmartMe", "EMS Module Disabled. Skipping getConsumption")
            return 0

        # Return consumption value
        return 0

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(10, "SmartMe", "EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getGenerationValues(self):
        url = "https://smart-me.com/api/DeviceBySerial?serial=" + self.serialNumber
        headers = {
            "content-type": "application/json",
        }

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            self.master.debugLog(10, "SmartMe", "Fetching SmartMe EMS sensor values")
            self.session = self.requests.Session()
            self.session.auth = (self.username, self.password)
            httpResponse = self.session.get(
                url, headers=headers, timeout=self.timeout
            )
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(4, "SmartMe", "Error connecting to SmartMe to fetching sensor values")
            self.master.debugLog(10, "SmartMe", str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            self.master.debugLog(4, "SmartMe", "Read Timeout occurred fetching SmartMe sensor values")
            self.master.debugLog(10, "SmartMe", str(e))
            self.fetchFailed = True
            return False

        jsonResponse = (
            httpResponse.json()
            if httpResponse and httpResponse.status_code == 200
            else None
        )

        if jsonResponse:
            self.generatedW = float(jsonResponse["ActivePower"])

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
