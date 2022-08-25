# SolarEdge Monitoring Portal Integration
import logging
import time
import solaredge_modbus

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
    inverterHost = None
    inverterPort = 1502
    smartMeters = []
    useModbusTCP = False

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
        self.inverterHost = self.configSolarEdge.get("inverterHost", self.inverterHost)
        self.inverterPort = int(
            self.configSolarEdge.get("inverterPort", self.inverterPort)
        )
        self.smartMeters = self.configSolarEdge.get("smartMeters", self.smartMeters)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (
            ((not self.siteID) or (not self.apiKey))
            and ((not self.inverterHost) or (not self.inverterPort))
        ):
            self.master.releaseModule("lib.TWCManager.EMS", "SolarEdge")
            return None

        if self.inverterHost and self.inverterPort:
            # basic syntax check for nested parameters
            for smartMeter in self.smartMeters:
                if not "name" in smartMeter:
                    logger.error(
                        "missing 'name' for SolarEdge smartMeter in config.json"
                        " - please specify (try 'Meter1', 'Meter2', 'Meter3')"
                    )
                    self.master.releaseModule("lib.TWCManager.EMS", "SolarEdge")
                    return None
                if not "type" in smartMeter or (
                    smartMeter["type"] != "consumption"
                    and smartMeter["type"] != "export"
                ):
                    logger.error(
                        "invalid or missing 'type' for SolarEdge smartMeter in "
                        "config.json - please specify as 'consumption' or 'export'"
                    )
                    self.master.releaseModule("lib.TWCManager.EMS", "SolarEdge")
                    return None

            # Drop the cacheTime to 10 seconds if we use local metering
            self.useModbusTCP = True
            self.cacheTime = 10

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

    def updateCloudAPI(self):

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
                            portalData["siteCurrentPowerFlow"]["LOAD"]["currentPower"]
                        )
                        * 1000
                    )
                    # Whether the Generation value is taken from this query or from the
                    # overview query depends on if we have determined whether consumption
                    # values are being reported or not
                    if self.pollMode == 0 or self.pollMode == 2:
                        self.generatedW = int(
                            float(
                                portalData["siteCurrentPowerFlow"]["PV"]["currentPower"]
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

    def updateModbusTCP(self):

        meteredConsumption = 0
        meteredExport = 0
        exportIsMetered = False

        # if we fail to update, we may be called again immediately
        # this will make pymodbus.c choke, so give it a second to relax
        if self.fetchFailed:
            time.sleep(1)

        inverter = solaredge_modbus.Inverter(
            host=self.inverterHost, port=self.inverterPort
        )
        # returns true/false, does not raise exception on connection error
        # but pymodbus.c logs an error already at least
        if not inverter.connect():
            logger.error(
                "failed to connect to inverter "
                f"{self.inverterHost!r} port {self.inverterPort!r}"
            )
            self.fetchFailed = True
            return

        # this should actually not fail unless SE changes its inverters or
        # maybe if there is a connection error during transmission
        # if we get a KeyError here, SE inverters and solaredge_modbus have
        # changed and we need to adapt the code to the new data structure
        try:
            power_ac = inverter.read("power_ac")["power_ac"]
            power_ac_scale = inverter.read("power_ac_scale")["power_ac_scale"]
            # solaredge_modbus doesn't raise Exceptions, it just returns False
            if power_ac is False or power_ac_scale is False:
                raise Exception("unable to get power_ac values")
            self.generatedW = int(power_ac * 10**power_ac_scale)
        except Exception as e:
            logger.error(f"failed to get AC power from inverter: {e!r}")
            self.fetchFailed = True
            inverter.disconnect()
            return

        # SE inverters can have three meters connected on the internal bus
        # names are hardcoded to Meter1, Meter2, Meter3 by solaredge_modbus
        for smartMeter in self.smartMeters:
            # response from meters() may be empty if communication with
            # inverter failed, or if there are just no meters connected
            # I don't see a possibility to determine the actual reason
            # as, again, solaredge_modbus doesn't raise Exceptions
            try:
                meter = inverter.meters()[smartMeter["name"]]
            except KeyError as e:
                logger.error(
                    f"smart meter {smartMeter['name']!r} not found "
                    "in modbus response from inverter"
                )
                self.fetchFailed = True
                inverter.disconnect()
                return
            # this should actually not fail unless SE changes its inverters or
            # maybe if there is a connection error during transmission
            # if we get a KeyError here, SE inverters and solaredge_modbus have
            # changed and we need to adapt the code to the new data structure
            try:
                power = meter.read("power")["power"]
                power_scale = meter.read("power_scale")["power_scale"]
                if power is False or power_scale is False:
                    raise Exception("unable to get power values")
                power = int(power * 10**power_scale)
            except Exception as e:
                logger.error(
                    "failed to get metered power for "
                    f"{smartMeter['name']!r} from inverter: {e!r}"
                )
                self.fetchFailed = True
                inverter.disconnect()
                return

            if smartMeter["type"] == "export":
                # export might be exactly zero, so we need to remember
                # by different means we have seen an export meter
                exportIsMetered = True
                meteredExport += power
            elif smartMeter["type"] == "consumption":
                meteredConsumption += power

        if exportIsMetered:
            self.consumedW = meteredConsumption + self.generatedW - meteredExport
        else:
            self.consumedW = meteredConsumption

        # if we reach this point, everything should have gone well
        self.fetchFailed = False
        inverter.disconnect()

    def update(self):

        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Portal.

            if self.useModbusTCP:
                self.updateModbusTCP()
            else:
                self.updateCloudAPI()

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
