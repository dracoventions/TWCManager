import logging
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SolarLog:

    # SolarLog EMS Module
    # Fetches Consumption and Generation details from SolarLog

    import requests

    cacheTime = 10
    config = None
    configConfig = None
    configSolarLog = None
    consumedW = 0
    excludeConsumedW = 0
    fetchFailed = False
    generatedW = 0
    lastFetch = 0
    master = None
    status = False
    serverIP = None
    excludeConsumptionInverters = []
    timeout = 2
    smartEnergyInvertersActive = []

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = master.config.get("config", {})
        self.configSolarLog = master.config["sources"].get("SolarLog", {})
        self.status = self.configSolarLog.get("enabled", False)
        self.serverIP = self.configSolarLog.get("serverIP", None)
        self.excludeConsumptionInverters = self.configSolarLog.get(
            "excludeConsumptionInverters", []
        )

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP):
            self.master.releaseModule("lib.TWCManager.EMS", "SolarLog")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("SolarLog EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW - self.excludeConsumedW

    def getGeneration(self):

        if not self.status:
            logger.debug("SolarLog EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

    def getConsumptionAndGenerationValues(self):
        url = "http://" + self.serverIP + "/getjp"
        headers = {"content-type": "application/json"}
        payload = '{"801":{"170":null, "175":null}}'

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching SolarLog EMS sensor values")
            httpResponse = self.requests.post(
                url, data=payload, headers=headers, timeout=self.timeout
            )
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4, "Error connecting to SolarLog to fetching sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4, "Read Timeout occurred fetching SolarLog sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        jsonResponse = (
            httpResponse.json()
            if httpResponse and httpResponse.status_code == 200
            else None
        )

        if jsonResponse:
            self.consumedW = float(jsonResponse["801"]["170"]["110"])
            self.generatedW = float(jsonResponse["801"]["170"]["101"])
            # If a the Smart Meter is not active - it should not decline the energy used
            # (because then there is something else using the energy)
            self.smartEnergyInvertersActive = self.excludeConsumptionInverters.copy()
            smartEnergyInvertersActiveIndex = 0
            logger.log(
                logging.INFO8,
                "SmartMeters found " + str(len(self.excludeConsumptionInverters)),
            )
            while smartEnergyInvertersActiveIndex < len(
                self.excludeConsumptionInverters
            ):
                inverterIndex = self.excludeConsumptionInverters[
                    smartEnergyInvertersActiveIndex
                ]
                # a value of 0 means that it is off
                if (
                    inverterIndex > 0
                    and int(
                        jsonResponse["801"]["175"][
                            str(smartEnergyInvertersActiveIndex)
                        ]["101"]
                    )
                    == 0
                ):
                    logger.log(
                        logging.INFO8,
                        "SmartMeter " + str(inverterIndex) + " is inactive",
                    )
                    self.smartEnergyInvertersActive.remove(inverterIndex)
                else:
                    logger.log(
                        logging.INFO8, "SmartMeter " + str(inverterIndex) + " is active"
                    )
                smartEnergyInvertersActiveIndex += 1

    def getInverterValues(self):
        if len(self.excludeConsumptionInverters) == 0:
            self.excludeConsumedW = 0
            return False

        url = "http://" + self.serverIP + "/getjp"
        headers = {"content-type": "application/json"}
        payload = '{"782":null}'

        # Update fetchFailed boolean to False before fetch attempt
        # This will change to true if the fetch failed, ensuring we don't then use the value to update our cache
        self.fetchFailed = False

        try:
            logger.debug("Fetching SolarLog EMS inverter values")
            httpResponse = self.requests.post(
                url, data=payload, headers=headers, timeout=self.timeout
            )
        except self.requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to SolarLog to fetching inverter values",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False
        except self.requests.exceptions.ReadTimeout as e:
            logger.log(
                logging.INFO4, "Read Timeout occurred fetching SolarLog inverter values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        jsonResponse = (
            httpResponse.json()
            if httpResponse and httpResponse.status_code == 200
            else None
        )
        if jsonResponse:
            tmpValue = 0
            for inverterIndex in self.smartEnergyInvertersActive:
                tmpValue = tmpValue + float(jsonResponse["782"][str(inverterIndex)])
            self.excludeConsumedW = tmpValue

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from SolarLog.
            self.getConsumptionAndGenerationValues()

            if self.fetchFailed is not True:
                self.getInverterValues()

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
