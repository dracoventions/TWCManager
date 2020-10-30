# Enphase Monitoring Portal Integration


class Enphase:

    import requests
    import time

    apiKey = None
    # cacheTime is a bit higher than local EMS modules
    # because we're polling an external API
    cacheTime = 60
    config = None
    configConfig = None
    configEnphase = None
    consumedW = 0
    debugLevel = 0
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
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configEnphase.get("enabled", False)
        self.systemID = self.configEnphase.get("systemID", None)
        self.userID = self.configEnphase.get("userID", None)

        # Unload if this module is disabled or misconfigured
        if (
            (not self.status)
            or (not self.systemID)
            or (not self.apiKey)
            or (not self.userID)
        ):
            self.master.releaseModule("lib.TWCManager.EMS", "Enphase")
            return None

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(
                10, "Enphase", "Enphase EMS Module Disabled. Skipping getConsumption"
            )
            return None

        # Perform updates if necessary
        self.update()

        # Return current generation value
        return float(self.generatedW)

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(
                10, "Enphase", "Enphase EMS Module Disabled. Skipping getGeneration"
            )
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getPortalData(self):
        url = "https://api.enphaseenergy.com/api/v2/systems/" + self.systemID
        url += "/summary?key=" + self.apiKey + "&user_id=" + self.userID

        return self.getPortalValue(url)

    def getPortalValue(self, url):

        # Fetch the specified URL from the Enphase Portal and return the data
        self.fetchFailed = False

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(
                4, "Enphase", "Error connecting to Enphase Portal to fetch sensor value"
            )
            self.master.debugLog(10, "Enphase", str(e))
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            self.master.debugLog(
                4,
                "Enphase",
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to Enphase Portal to fetch sensor value",
            )
            return ""
        else:
            return r.json()

    def update(self):

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            portalData = self.getPortalData()
            if portalData:
                try:
                    self.generatedW = int(portalData["current_power"])
                except (KeyError, TypeError) as e:
                    self.master.debugLog(
                        4,
                        "Enphase",
                        "Exception during parsing Enphase data (current_power)",
                    )
                    self.master.debugLog(10, "Enphase", e)
            else:
                self.master.debugLog(
                    4, "Enphase", "Enphase API result does not contain json content."
                )
                self.fetchFailed = True

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
