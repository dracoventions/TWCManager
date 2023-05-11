# Fronius Datamanager Solar.API Integration (Inverter Web Interface)
import logging
import requests
import time

logger = logging.getLogger("\U000026C5 Fronius")


class Fronius:
    cacheTime = 10
    config = None
    configConfig = None
    configFronius = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    serverIP = []
    serverPort = 80
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
            self.configFronius = master.config["sources"]["Fronius"]
        except KeyError:
            self.configFronius = {}
        self.status = self.configFronius.get("enabled", False)
        self.serverIP = self.configFronius.get("serverIP", None)
        self.serverPort = self.configFronius.get("serverPort", "80")

        # If serverIP is not a list, make it one
        if not isinstance(self.serverIP, list):
            self.serverIP = [self.serverIP]

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "Fronius")
            return None

    def getConsumption(self):
        if not self.status:
            logger.debug("Fronius EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value (negated, as this is how it's presented)
        return float(self.consumedW) * -1

    def getGeneration(self):
        if not self.status:
            logger.debug("Fronius EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        if not self.generatedW:
            self.generatedW = 0
        return float(self.generatedW)

    def getInverterData(self, inverter):
        url = "http://" + inverter + ":" + self.serverPort
        url = (
            url
            + "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceID=1&DataCollection=CommonInverterData"
        )

        return self.getInverterValue(url)

    def getInverterValue(self, url):
        # Fetch the specified URL from the Fronius Inverter and return the data
        self.fetchFailed = False

        try:
            r = requests.get(url, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to Fronius Inverter to fetch sensor value",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        r.raise_for_status()
        jsondata = r.json()
        return jsondata

    def getMeterData(self, inverter):
        url = "http://" + inverter + ":" + self.serverPort
        url = url + "/solar_api/v1/GetPowerFlowRealtimeData.fcgi?Scope=System"

        return self.getInverterValue(url)

    def update(self):
        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Fronius inverter.

            con = 0
            gen = 0
            for inverter in self.serverIP:
                inverterData = self.getInverterData(inverter)
                if inverterData:
                    try:
                        if "UAC" in inverterData["Body"]["Data"]:
                            self.voltage = inverterData["Body"]["Data"]["UAC"]["Value"]
                    except (KeyError, TypeError) as e:
                        logger.log(
                            logging.INFO4,
                            "Exception during parsing Inverter Data (UAC)",
                        )
                        logger.debug(e)

                meterData = self.getMeterData(inverter)
                if meterData:
                    try:
                        if "P_PV" in meterData["Body"]["Data"]["Site"]:
                            gen += float(meterData["Body"]["Data"]["Site"]["P_PV"])
                    except (KeyError, TypeError) as e:
                        logger.log(
                            logging.INFO4,
                            "Exception during parsing Meter Data (Generation)",
                        )
                        logger.debug(e)

                    try:
                        if "P_Load" in meterData["Body"]["Data"]["Site"]:
                            con += float(meterData["Body"]["Data"]["Site"]["P_Load"])
                    except (KeyError, TypeError) as e:
                        logger.log(
                            logging.INFO4,
                            "Exception during parsing Meter Data (Consumption)",
                        )
                        logger.debug(e)

            # Update values
            self.consumedW = con
            self.generatedW = gen

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
