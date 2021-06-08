# SolarEdge Monitoring Portal Integration
import logging
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SolarEdge:

    import requests

    apiKey = None
    # cacheTime is a bit higher than local EMS modules
    # because we're polling an external API, and the API has a limit of 300 requests per day
    cacheTime = 90
    config = None
    configConfig = None
    configSolarEdge = None
    consumedW = 0
    debugFile = "/tmp/twcmanager_solaredge_debug.txt"
    debugMode = 0
    fetchFailed = False
    generatedW = 0
    importW = 0
    exportW = 0
    lastFetch = 0
    master = None
    pollConsumption = 0
    pollCount = 0
    pollMode = 0
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
        self.debugFile = self.configConfig.get("debugFile", self.debugFile)
        self.debugMode = self.configSolarEdge.get("debugMode", self.debugMode)
        self.status = self.configSolarEdge.get("enabled", self.status)
        self.siteID = self.configSolarEdge.get("siteID", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.siteID) or (not self.apiKey):
            self.master.releaseModule("lib.TWCManager.EMS", "SolarEdge")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("SolarEdge EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return current consumed value
        return float(self.consumedW)

    def getGeneration(self):

        if not self.status:
            logger.debug("SolarEdge EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getPortalData(self, request):

        # Fetch the specified data from the SolarEdge Portal and return the data
        self.fetchFailed = False

        url = "https://monitoringapi.solaredge.com/site/" + self.siteID
        url += "/" + request + "?api_key=" + self.apiKey

        if self.debugMode:
            with open(self.debugFile, "a") as file:
                file.write(
                    "getPortalData requests: "
                    + str(request)
                    + "via URL: "
                    + str(url)
                    + "\n"
                )
            file.close()

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to SolarEdge Portal to fetch sensor value",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            logger.log(
                logging.INFO4,
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to SolarEdge Portal to fetch sensor value",
            )

            if self.debugMode:
                with open(self.debugFile, "a") as file:
                    file.write(
                        "getPortalData returns HTTPError exception, string will be returned as null. Exception details follow:\n"
                    )
                    file.write("HTTP Error Code: " + str(e.response.status_code) + "\n")
                    file.write("Full exception: " + str(e) + "\n")
            return ""
        else:
            if self.debugMode:
                with open(self.debugFile, "a") as file:
                    file.write("getPortalData returns " + str(r.content) + "\n")
                file.close()

            return r.json()

    def update(self):

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            # Query for Generation Data, if pollMode is set to 1
            # This is the higher resolution API endpoint, but it is for generation only
            # If the API detects no consumption data, it will step down to this.
            if self.pollMode == 1:
                portalData = self.getPortalData("overview")
                if portalData:
                    try:
                        self.generatedW = int(
                            portalData["overview"]["currentPower"]["power"]
                        )
                    except (KeyError, TypeError) as e:
                        logger.log(
                            logging.INFO4,
                            "Exception during parsing SolarEdge data (currentPower)",
                        )
                        logger.debug(e)
                else:
                    logger.log(
                        logging.INFO4,
                        "SolarEdge API result does not contain json content.",
                    )
                    self.fetchFailed = True

            # Query for consumption data
            # This query only executes if we're in pollMode 0 or 2. If we are in 1, we skip
            # Because consumption data is optional, we won't raise an error if it doesn't parse
            portalData = None
            if self.pollMode == 0 or self.pollMode == 2:
                portalData = self.getPortalData("currentPowerFlow")
            if portalData:
                try:
                    # The unit used is specified by the API
                    if portalData["siteCurrentPowerFlow"]["unit"] == "W":
                        self.consumedW = int(
                            portalData["siteCurrentPowerFlow"]["LOAD"]["currentPower"]
                        )
                        # Whether the Generation value is taken from this query or from the
                        # overview query depends on if we have determined whether consumption
                        # values are being reported or not
                        if self.pollMode == 0 or self.pollMode == 2:
                            self.generatedW = int(
                                portalData["siteCurrentPowerFlow"]["PV"]["currentPower"]
                            )
                    elif portalData["siteCurrentPowerFlow"]["unit"] == "kW":
                        self.consumedW = int(
                            float(
                                portalData["siteCurrentPowerFlow"]["LOAD"][
                                    "currentPower"
                                ]
                            )
                            * 1000
                        )
                        # Whether the Generation value is taken from this query or from the
                        # overview query depends on if we have determined whether consumption
                        # values are being reported or not
                        if self.pollMode == 0 or self.pollMode == 2:
                            self.generatedW = int(
                                float(
                                    portalData["siteCurrentPowerFlow"]["PV"][
                                        "currentPower"
                                    ]
                                )
                                * 1000
                            )

                    else:
                        logger.info(
                            "Unknown SolarEdge Consumption Value unit: %s "
                            % str(portalData["siteCurrentPowerFlow"]["unit"])
                        )

                except (KeyError, TypeError) as e:
                    logger.log(
                        logging.INFO4,
                        "Exception during parsing SolarEdge consumption data",
                    )
                    logger.debug(e)

            # Check if we are still in the initial poll period, and if so, record any consumption
            # reported to the pollconsumption counter. The reason for this is that if that value
            # rises at all, we lock in to consumption mode and do not query the overview API anymore
            if self.pollMode == 0 and self.pollCount <= 3:
                self.pollCount += 1
                self.pollConsumption += self.consumedW
            elif self.pollMode == 0:
                if self.pollConsumption:
                    logger.info(
                        "Detected consumption status capability. Switching to pollMode = 2"
                    )
                    self.pollMode = 2
                else:
                    logger.info(
                        "Detected no consumption status capability. Switching to pollMode = 1"
                    )
                    self.pollMode = 1

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())
            else:
                if self.debugMode:
                    with open(self.debugFile, "a+") as file:
                        file.write("fetchFailed is True\n")
                    file.close()

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
