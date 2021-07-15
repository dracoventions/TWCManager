# P1 Monitor API integration  (https://www.ztatz.nl/)

# This module takes an average of the last X (min 1, max 10) values deliverd by the P1 Monitor API.
# This makes that any spikes are not directly influence the behavior of TWCManager.

import logging
import array
import scipy.stats
import json
logger = logging.getLogger(__name__.rsplit(".")[-1])

class P1Monitor:
    import time
    import requests

    consumedW = 0
    generatedW = 0
    timeout = 10

    def __init__(self, master):

        try:
            self.configP1Mon = master.config["sources"]["P1Monitor"]
            self.serverIP = self.configP1Mon.get("serverIP", None)
            logger.log(logging.DEBUG2,"P1Monitor: serverIP: " + str(self.serverIP))
            self.samples = self.configP1Mon.get("samples", 1)
            logger.log(logging.DEBUG2,"P1Monitor: samples: " + str(self.samples))

        except (KeyError) as e:
            logger.error("Cannot get configuration for P1Monitor in config.json", e)

        # Unload if this module is disabled or misconfigured
        if not self.serverIP:
            logger.error("Cannot use P1Monitor module bacause it has no server ip configured!")
            master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

        # Unload if this module is disabled or misconfigured
        if self.samples < 1 or self.samples > 10 :
            logger.error("Cannot use P1Monitor module bacause the samples configured in config.json is not a value from 1 to 10!")
            master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

    def getConsumption(self):

        # Perform updates if necessary
        self.update()

        # Return current consumed value
        logger.log(logging.DEBUG2,"P1Monitor: consumedW (raw): " + str(self.consumedW))
        if self.consumedW > 0:
            return float(self.consumedW)
        else:
            return float(0)

    def getGeneration(self):

        # Perform updates if necessary
        self.update()

        # Return generation value
        logger.log(logging.DEBUG2,"P1Monitor: generatedW (raw): " + str(self.generatedW))
        if self.generatedW > 0:
            return float(self.generatedW)
        else:
            return float(0)


    def getP1MonAPIData(self):

        # Fetch the specified data from the P1Monitor API and return the data
        self.fetchFailed = False

        url = "http://" + self.serverIP + "/api/v1/phase?limit=" + str(self.samples) + "&json=object&round=on"
        logger.log(logging.DEBUG2,"P1Monitor: url: " + str(url))

        try:
            logger.log(logging.DEBUG2,"P1Monitor: timeout: " + str(self.timeout))
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

                    logger.log(logging.DEBUG2,"P1Monitor: API Json Output: " + json.dumps(p1monData))

                    # Calculate the avarage trimming 10% of the highest and lowest values https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.trim_mean.html
                    CONSUMPTION_L1_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['CONSUMPTION_L1_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: CONSUMPTION_L1_W_Avg: " + str(CONSUMPTION_L1_W_Avg))
                    CONSUMPTION_L2_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['CONSUMPTION_L2_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: CONSUMPTION_L2_W_Avg: " + str(CONSUMPTION_L2_W_Avg))
                    CONSUMPTION_L3_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['CONSUMPTION_L3_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: CONSUMPTION_L3_W_Avg: " + str(CONSUMPTION_L3_W_Avg))
                    PRODUCTION_L1_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['PRODUCTION_L1_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: PRODUCTION_L1_W_Avg: " + str(PRODUCTION_L1_W_Avg))
                    PRODUCTION_L2_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['PRODUCTION_L2_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: PRODUCTION_L2_W_Avg: " + str(PRODUCTION_L2_W_Avg))
                    PRODUCTION_L3_W_Avg = scipy.stats.trim_mean(array.array('i',(int(float(p1monData[i]['PRODUCTION_L3_W'])) for i in range(0,self.samples))),0.1)
                    logger.log(logging.DEBUG2,"P1Monitor: PRODUCTION_L3_W_Avg: " + str(PRODUCTION_L3_W_Avg))

                    #Get the max value of consumption, because we don't want to overload the fuse.
                    self.consumedW = int(
                        max([
                            CONSUMPTION_L1_W_Avg,
                            CONSUMPTION_L2_W_Avg,
                            CONSUMPTION_L3_W_Avg
                            ])
                    )
                    # Get the sum value of production, because it should be installed within the fuse configuration
                    # and we want to make use of all the power we produce.
                    self.generatedW = int(
                        sum([
                            PRODUCTION_L1_W_Avg,
                            PRODUCTION_L2_W_Avg,
                            PRODUCTION_L3_W_Avg
                            ])
                    )
            except (KeyError, TypeError) as e:
                logger.error("P1Monitor: Exception during parsing P1Monitor data", e)
        else:
            logger.error("P1Monitor: P1Monitor API result does not contain json content")

        return True


