# SolarEdge Monitoring Portal Integration


class SolarEdge:

    import requests
    import time

    apiKey = None
    # cacheTime is a bit higher than local EMS modules
    # because we're polling an external API
    cacheTime = 60
    config = None
    configConfig = None
    configSolarEdge = None
    consumedW = 0
    debugFile = "/tmp/twcmanager_solaredge_debug.txt"
    debugLevel = 0
    debugMode = 0
    fetchFailed = False
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    siteID = None
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
            self.configSolarEdge = master.config["sources"]["SolarEdge"]
        except KeyError:
            self.configSolarEdge = {}
        self.apiKey     = self.configSolarEdge.get("apiKey", None)
        self.debugFile  = self.configConfig.get("debugFile",  self.debugFile)
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.debugMode  = self.configSolarEdge.get("debugMode", self.debugMode)
        self.status     = self.configSolarEdge.get("enabled", self.status)
        self.siteID     = self.configSolarEdge.get("siteID", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.siteID) or (not self.apiKey):
            self.master.releaseModule("lib.TWCManager.EMS", "SolarEdge")
            return None

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(
                10,
                "SolarEdge",
                "SolarEdge EMS Module Disabled. Skipping getConsumption",
            )
            return 0

        # Perform updates if necessary
        self.update()

        # Return current consumed value
        return float(self.consumedW)

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(
                10, "SolarEdge", "SolarEdge EMS Module Disabled. Skipping getGeneration"
            )
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getPortalData(self, request):

        # Fetch the specified data from the SolarEdge Portal and return the data
        self.fetchFailed = False

        url = "https://monitoringapi.solaredge.com/site/" + self.siteID
        url += "/"+request+"?api_key=" + self.apiKey

        if self.debugMode:
            with open(self.debugFile, 'a') as file:
                file.write("getPortalData requests: "+str(request) + "via URL: "+ str(url) + "\n")
            file.close()

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(
                4,
                "SolarEdge",
                "Error connecting to SolarEdge Portal to fetch sensor value",
            )
            self.master.debugLog(10, "SolarEdge", str(e))
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            self.master.debugLog(
                4,
                "SolarEdge",
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to SolarEdge Portal to fetch sensor value",
            )

            if self.debugMode:
                with open(self.debugFile, 'a') as file:
                    file.write("getPortalData returns HTTPError exception, string will be returned as null. Exception details follow:\n")
                    file.write("HTTP Error Code: " + str(e.response.status_code) + "\n")
                    file.write("Full exception: " + str(e) + "\n")
            return ""
        else:
            if self.debugMode:
                with open(self.debugFile, 'a') as file:
                    file.write("getPortalData returns " + str(r.content) + "\n")
                file.close()

            return r.json()

    def update(self):

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            # Query for Generation Data
            portalData = self.getPortalData("overview")
            if portalData:
                try:
                    self.generatedW = int(
                        portalData["overview"]["currentPower"]["power"]
                    )
                except (KeyError, TypeError) as e:
                    self.master.debugLog(
                        4,
                        "SolarEdge",
                        "Exception during parsing SolarEdge data (currentPower)",
                    )
                    self.master.debugLog(10, "SolarEdge", e)
            else:
                self.master.debugLog(
                    4,
                    "SolarEdge",
                    "SolarEdge API result does not contain json content.",
                )
                self.fetchFailed = True

            # Query for consumption data
            # Because consumption data is optional, we won't raise an error if it doesn't parse
            portalData = self.getPortalData("currentPowerFlow")
            if portalData:
                try:
                    # The unit used is specified by the API
                    if portalData["siteCurrentPowerFlow"]["unit"] == "W":
                        self.consumedW = int(
                            portalData["siteCurrentPowerFlow"]["LOAD"]["currentPower"]
                        )
                    else:
                        self.master.debugLog(
                            1,
                            "SolarEdge",
                            "Unknown SolarEdge Consumption Value unit: %s " % str(portalData["siteCurrentPowerFlow"]["unit"]),
                        )

                except (KeyError, TypeError) as e:
                    self.master.debugLog(
                        4,
                        "SolarEdge",
                        "Exception during parsing SolarEdge consumption data",
                    )
                    self.master.debugLog(10, "SolarEdge", e)

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())
            else:
                if self.debugMode:
                    with open(self.debugFile, 'a+') as file:
                        file.write("fetchFailed is True\n")
                    file.close()

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
