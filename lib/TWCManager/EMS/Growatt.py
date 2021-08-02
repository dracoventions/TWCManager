import logging
import growattServer
import datetime


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
    useBatteryAt = None
    useBatteryTill = None
    batteryMaxOutput = None
    dischargingTill = None
    useBatteryBefore = None
    now = None

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = master.config.get("config", {})
        self.configGrowatt = master.config["sources"].get("Growatt", {})
        self.password = self.configGrowatt.get("password", "")
        self.status = self.configGrowatt.get("enabled", False)
        self.username = self.configGrowatt.get("username", "")
        self.useBatteryAt = float(self.configGrowatt.get("useBatteryAt", 0))
        self.useBatteryTill = float(self.configGrowatt.get("useBatteryTill", 0))
        self.batteryMaxOutput = float(self.configGrowatt.get("batteryMaxOutput", 0))
        timestring = self.configGrowatt.get("useBatteryBefore", "00:00")
        timelist = timestring.split(":")
        self.useBatteryBefore = datetime.time(int(timelist[0]), int(timelist[1]))
        self.discharginTill = self.useBatteryAt
        self.now = datetime.datetime.now().time()
        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.username or not self.password):
            self.master.releaseModule("lib.TWCManager.EMS", "Growatt")
            return None

    def getConsumption(self):  # gets called by TWCManager.py

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getConsumption")
            return 0

        # Perform updates if necessary
        self.update()

        # Return consumption value
        return self.consumedW

    def getGeneration(self):  # gets called by TWCManager.py

        if not self.status:
            logger.debug("EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return self.generatedW

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
            plant_list = api.plant_list(login_response["userId"])["data"][0]
            plant_ID = plant_list["plantId"]
            inverter = api.device_list(plant_ID)[0]
            deviceAilas = inverter["deviceAilas"]
            status = api.mix_system_status(deviceAilas, plant_ID)
            plant_info = api.plant_info(plant_ID)
            device = plant_info["deviceList"][0]
            device_sn = device["deviceSn"]
            mix_status = api.mix_system_status(device_sn, plant_ID)
            self.batterySOC = float(mix_status["SOC"])
            gen_calc = float(status["pPv1"]) + float(status["pPv2"])
            gen_calc *= 1000
            gen_api = float(status["ppv"]) * 1000
            inTime = (
                self.now > datetime.time(00, 00) and self.now < self.useBatteryBefore
            )
            if self.discharginTill < self.batterySOC and inTime:
                self.discharginTill = self.useBatteryTill
                self.generatedW = gen_api + self.batteryMaxOutput
            else:
                self.discharginTill = self.useBatteryAt
                self.generatedW = gen_api
            self.consumedW = float(status["pLocalLoad"]) * 1000
        else:
            logger.log(logging.INFO4, "No response from Growatt API")

    def setCacheTime(self, cacheTime):
        self.cacheTime = cacheTime

    def setTimeout(self, timeout):
        self.timeout = timeout

    def update(self):
        # Update function - determine if an update is required
        self.now = datetime.datetime.now().time()

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
