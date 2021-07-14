# P1 Monitor API integration  (https://www.ztatz.nl/)

import logging
logger = logging.getLogger(__name__.rsplit(".")[-1])

class P1Monitor:
    import time
    import json
    import requests

    consumedW = 0
    generatedW = 0
    timeout = 10

    def __init__(self, master):

        try:
            self.configP1Mon = master.config["sources"]["P1Monitor"]
            self.serverIP = self.configP1Mon.get("serverIP", None)
        except (KeyError) as e:
            logger.error("Cannot get configuration for P1Monitor in config.json", e)

        # Unload if this module is disabled or misconfigured
        if not self.serverIP:
            logger.error("Cannot use P1Monitor module bacause it has no server ip configured!")
            self.master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

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
            logger.error("P1Monitor: Error connecting to P1Monitor API to fetch sensor value")
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            logger.error("P1Monitor: HTTP status " + str(e.response.status_code) + " connecting to P1Monitor API to fetch sensor value")

        return r.json()

    def update(self):

        p1monData = self.getP1MonAPIData()
        if p1monData:
            try:
                    self.consumedW = int(
                        max([
                            int(float(p1monData[0]['CONSUMPTION_L1_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L2_W'])),
                            int(float(p1monData[0]['CONSUMPTION_L3_W']))
                            ])
                    )
                    self.generatedW = int(
                        max([
                            int(float(p1monData[0]['PRODUCTION_L1_W'])),
                            int(float(p1monData[0]['PRODUCTION_L2_W'])),
                            int(float(p1monData[0]['PRODUCTION_L3_W']))
                            ])
                    )
            except (KeyError, TypeError) as e:
                logger.error("P1Monitor: Exception during parsing P1Monitor data", e)
        else:
            logger.error("P1Monitor: P1Monitor API result does not contain json content")

        return True


