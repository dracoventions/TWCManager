# The Energy Detective (TED)
import logging
import re
import requests
import time


logger = logging.getLogger(__name__.rsplit(".")[-1])


class TED:

    # I check solar panel generation using an API exposed by The
    # Energy Detective (TED). It's a piece of hardware available
    # at http://www.theenergydetective.com

    cacheTime = 10
    config = None
    configConfig = None
    configTED = None
    consumedW = 0
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
        self.status = self.configTED.get("enabled", False)
        self.serverIP = self.configTED.get("serverIP", None)
        self.serverPort = self.configTED.get("serverPort", "80")

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "TED")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("TED EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # I don't believe this is implemented
        return float(0)

    def getGeneration(self):

        if not self.status:
            logger.debug("TED EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getTEDValue(self, url):

        # Fetch the specified URL from TED and return the data
        self.fetchFailed = False

        try:
            r = requests.get(url, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            logger.log(logging.INFO4, "Error connecting to TED to fetch solar data")
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        r.raise_for_status()
        return r

    def update(self):

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from HomeAssistant sensor.

            url = "http://" + self.serverIP + ":" + self.serverPort
            url = url + "/history/export.csv?T=1&D=0&M=1&C=1"

            value = self.getTEDValue(url)
            m = None
            if value:
                m = re.search(b"^Solar,[^,]+,-?([^, ]+),", value, re.MULTILINE)
            else:
                logger.log(logging.INFO5, "Failed to find value in response from TED")
                self.fetchFailed = True

            if m:
                self.generatedW = int(float(m.group(1)) * 1000)

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
