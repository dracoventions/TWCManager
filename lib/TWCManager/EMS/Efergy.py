# Efergy 


class Efergy:

    import requests
    import time

    cacheTime = 10
    config = None
    configConfig = None
    configEfergy = None
    consumedW = 0
    debugLevel = 0
    fetchFailed = False
    token=0
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    status = False
    timeout = 10
    voltage = 0

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configEfergy = master.config["sources"]["Efergy"]
        except KeyError:
            self.configEfergy = {}
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configEfergy.get("enabled", False)
        self.token = self.configEfergy.get("token", None)
        self.serverPort = self.configEfergy.get("serverPort", "80")

        # Unload if this module is disabled or misconfigured
        if (not self.status):
            self.master.releaseModule("lib.TWCManager.EMS", "Efergy")
            return None

    def debugLog(self, minlevel, message):
        self.master.debugLog(minlevel, "Efergy", message)

    def getConsumption(self):

        if not self.status:
            self.debugLog(10, "Efergy EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return float(self.consumedW)

    def getGeneration(self):

        if not self.status:
            self.debugLog(10, "Efergy EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        if not self.generatedW:
            self.generatedW = 0
        return float(self.generatedW)


    def getValue(self, url):

        # Fetch the specified URL from the Efergy and return the data
        self.fetchFailed = False

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.debugLog(
                4, "Error connecting to Efergy to fetch sensor value"
            )
            self.debugLog(10, str(e))
            self.fetchFailed = True
            return False

        r.raise_for_status()
        jsondata = r.json()
        return jsondata

    def getMeterData(self):
        url = "https://engage.efergy.com/mobile_proxy/getCurrentValuesSummary?token="+self.token

        return self.getValue(url)

    def update(self):

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Efergy.

            meterData = self.getMeterData()

            if meterData:
                try:
                    self.consumedW = list(meterData[0]['data'][0].values())[0]
                except (KeyError, TypeError) as e:
                    self.debugLog(
                        4, "Exception during parsing Meter Data (Consumption)"
                    )
                    self.debugLog(10, e)

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
