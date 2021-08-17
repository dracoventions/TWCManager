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

        self.p1monData = {}
        self.configP1Mon = master.config["sources"].get("P1Monitor", {})
        self.serverIP = self.configP1Mon.get("serverIP", None)
        self.samples = self.configP1Mon.get("samples", 1)

        # Unload if this module is disabled or misconfigured
        if not self.serverIP:
            logger.error(
                "Cannot use P1Monitor module bacause it has no server ip configured!"
            )
            master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

        # Unload if this module is disabled or misconfigured
        if self.samples < 1 or self.samples > 10:
            logger.error(
                "Cannot use P1Monitor module bacause the samples configured in config.json is not a value from 1 to 10!"
            )
            master.releaseModule("lib.TWCManager.EMS", "P1Monitor")
            return None

    def getConsumption(self):

        # Perform updates if necessary
        self.caller = "getConsumption"
        self.update()

        # Return current consumed value
        logger.log(logging.INFO2, "P1Monitor: consumedW (raw): " + str(self.consumedW))
        if self.consumedW > 0:
            return float(self.consumedW)
        else:
            return float(0)

    def getGeneration(self):

        # Perform updates if necessary
        self.caller = "getGeneration"
        self.update()

        # Return generation value
        logger.log(
            logging.INFO2, "P1Monitor: generatedW (raw): " + str(self.generatedW)
        )
        if self.generatedW > 0:
            return float(self.generatedW)
        else:
            return float(0)

    def getP1MonAPIData(self):

        # Fetch the specified data from the P1Monitor API and return the data
        self.fetchFailed = False

        url = (
            "http://"
            + self.serverIP
            + "/api/v1/phase?limit="
            + str(self.samples)
            + "&json=object&round=on"
        )
        logger.log(logging.INFO2, "P1Monitor: url: " + str(url))

        try:
            logger.log(logging.INFO2, "P1Monitor: timeout: " + str(self.timeout))
            r = self.requests.get(url, timeout=self.timeout)
        except self.requests.exceptions.ConnectionError as e:
            logger.error(
                "P1Monitor: Error connecting to P1Monitor API to fetch sensor value"
            )
            return False

        try:
            r.raise_for_status()
        except self.requests.exceptions.HTTPError as e:
            logger.error(
                "P1Monitor: HTTP status "
                + str(e.response.status_code)
                + " connecting to P1Monitor API to fetch sensor value"
            )

        return r.json()

    def update(self):

        if not self.p1monData or self.caller == "getConsumption":
            logger.log(
                logging.INFO2, "P1Monitor: Refreshing data. Caller: " + self.caller
            )
            self.p1monData = self.getP1MonAPIData()
        else:
            logger.log(
                logging.INFO2, "P1Monitor: Using existing data. Caller: " + self.caller
            )

        if self.p1monData:
            try:

                logger.log(
                    logging.INFO3,
                    "P1Monitor: API Json Output: " + json.dumps(self.p1monData),
                )

                # Calculate the avarage trimming 10% of the highest and lowest values https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.trim_mean.html
                CONSUMPTION_L1_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["CONSUMPTION_L1_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: CONSUMPTION_L1_W_Avg: " + str(CONSUMPTION_L1_W_Avg),
                )
                CONSUMPTION_L2_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["CONSUMPTION_L2_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: CONSUMPTION_L2_W_Avg: " + str(CONSUMPTION_L2_W_Avg),
                )
                CONSUMPTION_L3_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["CONSUMPTION_L3_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: CONSUMPTION_L3_W_Avg: " + str(CONSUMPTION_L3_W_Avg),
                )
                PRODUCTION_L1_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["PRODUCTION_L1_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: PRODUCTION_L1_W_Avg: " + str(PRODUCTION_L1_W_Avg),
                )
                PRODUCTION_L2_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["PRODUCTION_L2_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: PRODUCTION_L2_W_Avg: " + str(PRODUCTION_L2_W_Avg),
                )
                PRODUCTION_L3_W_Avg = scipy.stats.trim_mean(
                    array.array(
                        "i",
                        (
                            int(float(self.p1monData[i]["PRODUCTION_L3_W"]))
                            for i in range(0, self.samples)
                        ),
                    ),
                    0.1,
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: PRODUCTION_L3_W_Avg: " + str(PRODUCTION_L3_W_Avg),
                )

                L1_V = int(float(self.p1monData[1]["L1_V"]))
                logger.log(logging.INFO2, "P1Monitor: L1_V: " + str(L1_V) + "V")
                L2_V = int(float(self.p1monData[1]["L2_V"]))
                logger.log(logging.INFO2, "P1Monitor: L2_V: " + str(L2_V) + "V")
                L3_V = int(float(self.p1monData[1]["L3_V"]))
                logger.log(logging.INFO2, "P1Monitor: L3_V: " + str(L3_V) + "V")

                phases = 1
                # Find out how many phases there are, because P1 Monitor does not report it.
                totalVolt = int(sum([L1_V, L2_V, L3_V]))
                maxVolt = int(max([L1_V, L2_V, L3_V]))
                minVolt = int(min([L1_V, L2_V, L3_V]))
                logger.log(
                    logging.INFO2,
                    "P1Monitor: Volt sum all phases: " + str(totalVolt) + "V",
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: Highest by a phase: " + str(maxVolt) + "V",
                )
                logger.log(
                    logging.INFO2, "P1Monitor: Lowest by a phase: " + str(minVolt) + "V"
                )
                if totalVolt > maxVolt:
                    phases = 3
                    logger.log(
                        logging.INFO2,
                        "P1Monitor: Determined "
                        + str(phases)
                        + " phases. Reason: Sum of all voltages ("
                        + str(totalVolt)
                        + "V) > than the highest voltage ("
                        + str(maxVolt)
                        + "V) reported",
                    )

                elif (totalVolt == maxVolt) or (minVolt == 0):
                    phases = 1
                    logger.log(
                        logging.INFO2,
                        "P1Monitor: Determined "
                        + str(phases)
                        + " phases. Reason: Sum of all voltages ("
                        + str(totalVolt)
                        + "V) == the highest volt ("
                        + str(maxVolt)
                        + " V) reported or the lowest voltage == 0 (Reported: "
                        + str(minVolt)
                        + " V).",
                    )
                else:
                    logger.error(
                        logging.error,
                        "P1Monitor: Cannot determine 1 or 3 phases! Check output of P1Monitor phase API! (Reported: L1_V: "
                        + str(L1_V)
                        + "V , L2_V: "
                        + str(L2_V)
                        + "V , L3_V: "
                        + str(L3_V)
                        + "V)",
                    )

                # Get the sum value of consumption through all phases. TWCManager self will devide the total usage over phases. We will report the maximum loaded phase multiplied by the amount of phases so we never overload a single phase.
                consumedW = int(
                    max(
                        [
                            CONSUMPTION_L1_W_Avg,
                            CONSUMPTION_L2_W_Avg,
                            CONSUMPTION_L3_W_Avg,
                        ]
                    )
                )
                logger.log(
                    logging.INFO2,
                    "P1Monitor: Phase with highest load consumes: "
                    + str(consumedW)
                    + "W",
                )

                # Report the consumption
                self.consumedW = consumedW * int(phases)

                # Report the generation
                self.generatedW = int(
                    sum([PRODUCTION_L1_W_Avg, PRODUCTION_L2_W_Avg, PRODUCTION_L3_W_Avg])
                )
            except (KeyError, TypeError) as e:
                logger.error("P1Monitor: Exception during parsing P1Monitor data", e)
        else:
            logger.error(
                "P1Monitor: P1Monitor API result does not contain json content"
            )

        return True
