import logging
import growattServer
        

logger = logging.getLogger(__name__.rsplit(".")[-1])


class Growatt:

    # Growatt EMS Module
    # Fetches Consumption and Generation details from Growatt API

    import requests
    import time

    cacheTime = 10
    config = None
    configConfig = None
    configGrowatt = None
    batterySOC = 0
    consumedW = 0
    fetchFailed = False
    generatedW = 0
    lastFetch = 0
    master = None
    password = None
    session = None
    status = False
    timeout = 2
    username = None

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = master.config.get("config", {})
        self.configGrowatt = master.config["sources"].get("Growatt", {})
        self.password = self.configGrowatt.get("password", "")
        self.status = self.configGrowatt.get("enabled", False)
        self.username = self.configGrowatt.get("username", "")

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (
            not self.username or not self.password
        ):
            self.master.releaseModule("lib.TWCManager.EMS", "Growatt")
            return None

    def getConsumption(self):

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getConsumption")
            return 0

       # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW 


    def getGeneration(self):

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        if self.generatedW > 0:
            return self.generatedW
        else:
            return 0

    def getGenerationValues(self):
        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getGeneration")
            return 0
        api = growattServer.GrowattApi()


        try:
            logger.debug("Fetching Growatt EMS sensor values")
            login_response = api.login(self.username, self.password)
        except Exception as e:
            logger.log(
                logging.INFO4, "Error connecting to Growatt to fetching sensor values"
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        if not login_response:
            logger.log(logging.INFO4, "Empty Response from Growatt API")
            return False

        if login_response:
            plant_list = api.plant_list(login_response['userId'])['data'][0]
            plant_ID= plant_list['plantId']
            inverter= api.device_list(plant_ID)[0]
            deviceAilas = inverter["deviceAilas"]
            datalog_sn = inverter["datalogSn"]
            status = api.mix_system_status(deviceAilas, plant_ID)
            plant_info=api.plant_info(plant_ID)
            device = plant_info['deviceList'][0]
            device_sn = device['deviceSn']
            mix_status = api.mix_system_status(device_sn, plant_ID)
            self.generatedW = calc_pv_total = (float(status['pPv1']) + float(status['pPv2'])) 
            self.consumedW = float(status['pLocalLoad'])*1000
            self.batterySOC = float(mix_status['SOC'])
        else:
            logger.log(logging.INFO4, "No JSON response from Growatt API")

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required

        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from Growatt.
            self.getGenerationValues()

            # Update last fetch time
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
