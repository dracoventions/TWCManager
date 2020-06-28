# SolarEdge Monitoring Portal Integration

class SolarEdge:

    import xml.etree.ElementTree as ET
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
    debugLevel = 0
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
        self.apiKey = self.configSolarEdge.get("apiKey", None)
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.status = self.configSolarEdge.get("enabled", False)
        self.siteID = self.configSolarEdge.get("siteID", None)

        # Unload if this module is disabled or misconfigured
        if ((not self.status) or (not self.siteID) 
           or (not self.apiKey)):
          self.master.releaseModule("lib.TWCManager.EMS","SolarEdge");

    def getConsumption(self):

        if not self.status:
            self.master.debugLog(10, "SolarEdge", "SolarEdge EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return current generation value
        return float(self.generatedW)

    def getGeneration(self):

        if not self.status:
            self.master.debugLog(10, "SolarEdge", "SolarEdge EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getPortalData(self):
        url = "http://monitoringapi.solaredge.com/site/"+ self.siteID
        url += "/overview?api_key="+ self.apiKey

        return self.getPortalValue(url)

    def getPortalValue(self, url):

        # Fetch the specified URL from the SolarEdge Portal and return the data
        self.fetchFailed = False

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            self.master.debugLog(
                4, "SolarEdge", 
                "Error connecting to SolarEdge Portal to fetch sensor value"
            )
            self.master.debugLog(10, "SolarEdge", str(e))
            self.fetchFailed = True
            return False

        r.raise_for_status()
        xmldata = self.ET.fromstring(r.content)
        return xmldata

    def update(self):

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            portalData = self.getPortalData()
            if portalData:
              cpwr = xmldata.find('./currentPower/power') 
              if cpwr:
                try:
                    self.generatedW = int(cpwr.text)
                except (KeyError, TypeError) as e:
                    self.master.debugLog(
                        4, "SolarEdge", 
                        "Exception during parsing SolarEdge data (currentPower)")
                    self.master.debugLog(10, "SolarEdge", e)
              else:
                self.master.debugLog(4, "SolarEdge", "SolarEdge API result does not contain currentPower/power XML node. Keys are:")
                self.master.debugLog(4, "SolarEdge", portalData.keys())
                self.fetchFailed = True

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
