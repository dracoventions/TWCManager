# P1 Monitor API integration  (https://www.ztatz.nl/)

import logging
logger = logging.getLogger(__name__.rsplit(".")[-1])

class P1Monitor:
    import time
    import json
    import requests

    config = None
    configConfig = None
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    master = None
    timeout = 10

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configP1Mon = master.config["sources"]["P1Monitor"]
            self.serverIP = self.configP1Mon.get("serverIP", None)
        except KeyError:
            logger.error("Cannot find serverIP for P1Monitor in config.json")
        try:
            self.configP1Mon = master.config["sources"]["P1Monitor"]
            self.mode = self.configP1Mon.get("mode", "TrackGreenEnergy")
        except KeyError:
            logger.error("Cannot find mode (LoadBalancing/TrackGreenEnergy) for P1Monitor in config.json")

        try:
            self.configP1Mon = master.config["sources"]["P1Monitor"]
            self.maxAmpsPerPhase = self.configP1Mon.get("maxAmpsPerPhase", 10)
        except KeyError:
            logger.error("Cannot find maxAmpsPerPhase value for P1Monitor in config.json")

        # Unload if this module is disabled or misconfigured
        if not self.serverIP:
            logger.warning("Cannot use P1Monitor module bacause it has no server ip configured!")
            self.master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None
        if self.mode.tolower() not in ["loadbalancing","trackgreenenergy"] :
            logger.warning("Mode must be set to LoadBalancing or TrackGreenEnergy")
            self.master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

    def maxWatt(self):
        p1monData = self.getP1MonAPIData()
        L1_V = int(float(p1monData[0]['L1_V']))
        L2_V = int(float(p1monData[0]['L2_V']))
        L3_V = int(float(p1monData[0]['L3_V']))

        return max([
            L1_V * int(self.maxAmpsPerPhase),
            L2_V * int(self.maxAmpsPerPhase),
            L3_V * int(self.maxAmpsPerPhase)
            ])

    def getConsumption(self):

        # Perform updates if necessary
        self.update()

        # Return current consumed value
        return float(self.consumedW)

    def getGeneration(self):

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.generatedW)

    def getP1MonAPIData(self):

        # Fetch the specified data from the P1Monitor API and return the data
        self.fetchFailed = False

        url = "http://" + self.serverIP + "/api/v1/phase?limit=1&json=object&round=on"

        try:
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.error(
                4,
                "P1Monitor",
                "Error connecting to P1Monitor API to fetch sensor value",
            )
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            logger.error(
                4,
                "P1Monitor",
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to P1Monitor API to fetch sensor value",
            )

        return r.json()

    def update(self):
        # This module support loadbalancing. So when mode is set to LoadBalancing it will manipulate the generatedW to
        # force TWCManager pumping up the amps to achive the maximum amount of Amps available on the net.
        # By default the maximum amount of Amps is set to 10A.

        p1monData = self.getP1MonAPIData()
        if p1monData:
            try:
                if self.mode.lower() == "loadbalancing":

                    L1_V = int(float(p1monData[0]['L1_V']))
                    L2_V = int(float(p1monData[0]['L2_V']))
                    L3_V = int(float(p1monData[0]['L3_V']))

                    maxWattAvailable = int(
                        max([
                            L1_V * int(self.maxAmpsPerPhase),
                            L2_V * int(self.maxAmpsPerPhase),
                            L3_V * int(self.maxAmpsPerPhase)
                            ])
                    )

                    consumedW = int(
                        max([
                            int(float(p1monData[0]['CONSUMPTION_L1_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L2_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L3_W']))
                            ])
                    )
                    generatedW = int(
                        max([
                            int(float(p1monData[0]['PRODUCTION_L1_W'])),
                            int(float(p1monData[0]['PRODUCTION_L2_W'])),
                            int(float(p1monData[0]['PRODUCTION_L3_W']))
                            ])
                    )

                    if consumedW >= maxWattAvailable:
                        availableW = 0
                    else:
                        availableW = maxWattAvailable - (consumedW + generatedW)

                    self.consumedW = sum(consumedW )
                    self.generatedW = sum(consumedW )

                else:
                    #TrackGreenEnergy
                    # We don't want to overload each phase. Therefor we'll use the maxAmpsPerPhase config.json attribute to check against.

                    self.consumedW = int(
                        max([
                            int(float(p1monData[0]['CONSUMPTION_L1_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L2_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L3_W']))
                            ])
                    )
                    self.generatedW = int(
                        #Sum all values because we want make use of all power generated
                        sum([
                            int(float(p1monData[0]['PRODUCTION_L1_W'])),
                            int(float(p1monData[0]['PRODUCTION_L2_W'])),
                            int(float(p1monData[0]['PRODUCTION_L3_W']))
                            ])
                    )
            except (KeyError, TypeError) as e:
                logger.debug(
                    4,
                    "P1Monitor",
                    "Exception during parsing P1Monitor data (consumedW)",
                )
                logger.debug(10, "P1Monitor", e)
        else:
            logger.debug(
                4,
                "P1Monitor",
                "P1Monitor API result does not contain json content.",
            )
            self.fetchFailed = True

        return True


