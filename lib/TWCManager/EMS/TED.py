# The Energy Detective (TED)


class TED:

    # I check solar panel generation using an API exposed by The
    # Energy Detective (TED). It's a piece of hardware available
    # at http://www.theenergydetective.com

    import re
    import requests
    import time

    cacheTime = 10
    config = None
    configConfig = None
    configTED = None
    consumedW = 0
    debugLevel = 0
    fetchFailed = False
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    serverIP = None
    serverPort = 80
    status = False
    timeout = 10
    voltage = 0

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = self.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configTED = self.config["sources"]["TED"]
        except KeyError:
            self.configTED = {}
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configTED.get("enabled", False)
        self.serverIP = self.configTED.get("serverIP", None)
        self.serverPort = self.configTED.get("serverPort", "80")

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "TED")
            return None

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(10, "TED", "TED EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # I don't believe this is implemented
        return float(0)

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(10, "TED", "TED EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getTEDValue(self, url):

        # Fetch the specified URL from TED and return the data
        self.fetchFailed = False

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(4, "TED", "Error connecting to TED to fetch solar data")
            self.master.debugLog(10, "TED", str(e))
            self.fetchFailed = True
            return False

        r.raise_for_status()
        return r

    def update(self):

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from HomeAssistant sensor.

            url = "http://" + self.serverIP + ":" + self.serverPort
            url = url + "/history/export.csv?T=1&D=0&M=1&C=1"

            value = self.getTEDValue(url)
            m = None
            if value:
                m = self.re.search(
                    b"^Solar,[^,]+,-?([^, ]+),", value, self.re.MULTILINE
                )
            else:
                self.master.debugLog(5, "TED", "Failed to find value in response from TED")
                self.fetchFailed = True

            if m:
                self.generatedW = int(float(m.group(1)) * 1000)

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
