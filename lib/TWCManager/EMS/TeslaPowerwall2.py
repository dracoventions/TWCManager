# Tesla Powerwall 2 EMS Module
import logging
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class TeslaPowerwall2:

    import requests
    import urllib3
    import json as json

    cacheTime = 10
    cloudCacheTime = 1800
    config = None
    configConfig = None
    configPowerwall = None
    master = None
    minSOE = 90
    lastFetch = dict()
    password = None
    serverIP = None
    serverPort = 443
    status = False
    timeout = 10
    tokenTimeout = 0
    httpSession = None
    cloudID = None
    suppressGeneration = False

    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.configConfig = self.config.get("config", dict())
        self.configPowerwall = self.config.get("sources", dict()).get(
            "Powerwall2", dict()
        )
        self.status = self.configPowerwall.get("enabled", False)
        self.serverIP = self.configPowerwall.get("serverIP", None)
        self.serverPort = self.configPowerwall.get("serverPort", "443")
        self.password = self.configPowerwall.get("password", None)
        self.minSOE = self.configPowerwall.get("minBatteryLevel", 0)
        self.cloudID = self.configPowerwall.get("cloudID", None)
        self.cloudCacheTime = self.configConfig.get("cloudUpdateInterval", 1800)
        self.httpSession = self.requests.session()
        if self.status and logger.getEffectiveLevel() > 9:
            # PW uses self-signed certificates; squelch warnings
            self.urllib3.disable_warnings(
                category=self.urllib3.exceptions.InsecureRequestWarning
            )

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serverIP) or (int(self.serverPort) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "TeslaPowerwall2")
            return None

    @property
    def generatedW(self):
        value = self.getPWValues()
        return float(value.get("solar", dict()).get("instant_power", 0))

    @property
    def consumedW(self):
        value = self.getPWValues()
        return float(value.get("load", dict()).get("instant_power", 0))

    @property
    def importW(self):
        value = self.getPWValues()
        gridW = float(value.get("site", dict()).get("instant_power", 0))
        return gridW if gridW > 0 else 0

    @property
    def exportW(self):
        value = self.getPWValues()
        gridW = float(value.get("site", dict()).get("instant_power", 0))
        return abs(gridW) if gridW < 0 else 0

    @property
    def gridStatus(self):
        value = self.getStatus()
        # There are actually two types of disconnected, but let's simplify that away
        return True if value.get("grid_status", "") == "SystemGridConnected" else False

    @property
    def voltage(self):
        value = self.getPWValues()
        return int(value.get("site", dict()).get("instant_average_voltage", 0))

    @property
    def batteryLevel(self):
        value = self.getSOE()
        return self.adjustPercentage(float(value.get("percentage", 0)))

    @property
    def operatingMode(self):
        value = self.getOperation()
        return value.get("real_mode", "")

    @property
    def reservePercent(self):
        if self.operatingMode == "backup":
            return float(96)
        else:
            value = self.getOperation()
            return self.adjustPercentage(float(value.get("backup_reserve_percent", 0)))

    @property
    def stormWatch(self):
        value = self.getStormWatch()
        return value.get("storm_mode_active", False)

    def adjustPercentage(self, raw_value):
        return (raw_value - 5) / 0.95

    def doPowerwallLogin(self):
        # If we have password authentication configured, this function will submit
        # the login details to the Powerwall API, and get an authentication token.
        # If we already have an authentication token, we just use that.
        if self.password is not None:
            if self.tokenTimeout < time.time():
                logger.log(logging.INFO6, "Logging in to Powerwall API")
                headers = {"Content-Type": "application/json"}
                data = {
                    "username": "customer",
                    "password": self.password,
                    "force_sm_off": False,
                }
                url = "https://" + self.serverIP + ":" + self.serverPort
                url += "/api/login/Basic"
                try:
                    req = self.httpSession.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=self.timeout,
                        verify=False,
                    )
                except self.requests.exceptions.ConnectionError as e:
                    logger.log(
                        logging.INFO4,
                        "Error connecting to Tesla Powerwall 2 for API login",
                    )
                    logger.debug(str(e))
                    return False

                # Time out token after one hour
                self.tokenTimeout = time.time() + (60 * 60)

                # After authentication, start Powerwall
                # If we don't do this, the Powerwall will stop working after login
                self.startPowerwall()

            else:
                logger.log(
                    logging.INFO6,
                    "Powerwall2 API token still valid for "
                    + str(self.tokenTimeout - time.time())
                    + " seconds.",
                )

    def getConsumption(self):

        if not self.status:
            logger.debug("Powerwall2 EMS Module Disabled. Skipping getConsumption")
            return 0

        # Return consumption value
        return float(self.consumedW)

    def getGeneration(self):

        if not self.status:
            logger.debug("Powerwall2 EMS Module Disabled. Skipping getGeneration")
            return 0

        if self.batteryLevel > (self.minSOE * 1.05):
            self.suppressGeneration = False
        if self.batteryLevel < (self.minSOE * 0.95):
            self.suppressGeneration = True

            # Battery is below threshold; leave all generation for PW charging
            logger.log(logging.INFO5, "Powerwall needs to charge. Ignoring generation.")

        if self.suppressGeneration:
            return 0

        # Return generation value
        return float(self.generatedW)

    def getPWJson(self, path):

        (lastTime, lastData) = (
            self.lastFetch[path] if path in self.lastFetch else (0, dict())
        )

        if (int(time.time()) - lastTime) > self.cacheTime:

            # Fetch the specified URL from Powerwall and return the data

            # Get a login token, if password authentication is enabled
            self.doPowerwallLogin()

            url = "https://" + self.serverIP + ":" + self.serverPort + path
            headers = dict()

            try:
                r = self.httpSession.get(
                    url, headers=headers, timeout=self.timeout, verify=False
                )
                r.raise_for_status()
            except Exception as e:
                if hasattr(e, "response") and e.response.status_code == 403:
                    logger.info("Authentication required to access local Powerwall API")
                    self.tokenTimeout = 0
                else:
                    logger.log(
                        logging.INFO4,
                        "Error connecting to Tesla Powerwall 2 to fetch " + path,
                    )
                    logger.debug(str(e))
                return lastData

            lastData = r.json()
            self.lastFetch[path] = (time.time(), r.json())

        return lastData

    def getPWValues(self):
        return self.getPWJson("/api/meters/aggregates")

    def getSOE(self):
        return self.getPWJson("/api/system_status/soe")

    def getOperation(self):
        return self.getPWJson("/api/operation")

    def getStatus(self):
        return self.getPWJson("/api/system_status/grid_status")

    def getStormWatch(self):
        carapi = self.master.getModuleByName("TeslaAPI")
        token = carapi.getCarApiBearerToken()
        expiry = carapi.getCarApiTokenExpireTime()
        now = time.time()
        key = "CLOUD/live_status"

        (lastTime, lastData) = (
            self.lastFetch[key] if key in self.lastFetch else (0, dict())
        )

        if (int(time.time()) - lastTime) > self.cloudCacheTime:

            if token and now < expiry:
                headers = {
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                }
                if not self.cloudID:
                    url = "https://owner-api.teslamotors.com/api/1/products"
                    bodyjson = None
                    products = list()

                    try:
                        r = self.httpSession.get(url, headers=headers)
                        r.raise_for_status()
                        bodyjson = r.json()
                        products = [
                            (i["energy_site_id"], i["site_name"])
                            for i in bodyjson["response"]
                            if "battery_type" in i
                            and i["battery_type"] == "ac_powerwall"
                        ]
                    except:
                        pass

                    if len(products) == 1:
                        (site, name) = products[0]
                        self.cloudID = site
                    elif len(products) > 1:
                        logger.info(
                            "Multiple Powerwall sites linked to your Tesla account.  Please specify the correct site ID in your config.json."
                        )
                        for (site, name) in products:
                            logger.info(f"   {site}: {name}")
                    else:
                        logger.info("Couldn't find a Powerwall on your Tesla account.")

                if self.cloudID:
                    url = f"https://owner-api.teslamotors.com/api/1/energy_sites/{self.cloudID}/live_status"
                    bodyjson = None
                    result = dict()

                    try:
                        r = self.httpSession.get(url, headers=headers)
                        r.raise_for_status()
                        bodyjson = r.json()
                        lastData = bodyjson["response"]
                    except:
                        pass

            self.lastFetch[key] = (now, lastData)
        return lastData

    def startPowerwall(self):
        # This function will instruct the powerwall to run.
        # This is needed after getting a login token for v1.15 and above

        # Get a login token, if password authentication is enabled
        self.doPowerwallLogin()

        url = "https://" + self.serverIP + ":" + self.serverPort
        url += "/api/sitemaster/run"
        headers = dict()

        try:
            r = self.httpSession.get(
                url, headers=headers, timeout=self.timeout, verify=False
            )
        except self.requests.exceptions.ConnectionError as e:
            logger.log(logging.INFO4, "Error instructing Tesla Powerwall 2 to start")
            logger.debug(str(e))
            return False
