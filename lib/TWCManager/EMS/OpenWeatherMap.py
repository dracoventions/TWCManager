# OpenWeatherMap,py module for TWCManager by GMerg
import logging
import requests
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class OpenWeatherMap:

    cacheTime = 60
    config = None
    configConfig = None
    configOpenWeatherMap = None
    fetchFailed = False
    generatedW = 0
    consumedW = 0
    lastFetch = 0
    master = None
    APIKey = None
    Latitude = 0
    Longitude = 0
    status = False
    timeout = 10
    PeakKW = None
    LastJson = None

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configOpenWeatherMap = master.config["sources"]["OpenWeatherMap"]
        except KeyError:
            self.configOpenWeatherMap = {}

        self.status = self.configOpenWeatherMap.get("enabled", False)
        self.Latitude = self.configOpenWeatherMap.get("Latitude", 0)
        self.Longitude = self.configOpenWeatherMap.get("Longitude", 0)
        self.APIKey = self.configOpenWeatherMap.get("APIKey", None)
        self.PeakKW = self.configOpenWeatherMap.get("PeakKW", None)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.APIKey):
            self.master.releaseModule("lib.TWCManager.EMS", "OpenWeatherMap")
            return None

    def getConsumption(self):
        # since this is not knowing our consumption!
        return 0

    def getGeneration(self):

        if not self.status:
            logger.debug("OpenWeatherMap EMS Module Disabled. Skipping getGeneration")
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        if not self.generatedW:
            self.generatedW = 0
        return float(self.generatedW)

    def getOpenWeatherMapData(self):
        url = (
            "https://api.openweathermap.org/data/2.5/onecall?lat="
            + str(self.Latitude)
            + "&lon="
            + str(self.Longitude)
            + "&appid="
            + self.APIKey
            + "&exclude=minutely&units=metric"
        )

        return self.getOpenWeatherMapValue(url)

    def getOpenWeatherMapValue(self, url):

        # Fetch the specified URL from the OpenWeatherMap and return the data
        self.fetchFailed = False

        try:
            r = requests.get(url, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            logger.log(
                logging.INFO4,
                "Error connecting to OpenWeatherMap to fetch sensor value",
            )
            logger.debug(str(e))
            self.fetchFailed = True
            return False

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.log(
                logging.INFO4,
                "HTTP status "
                + str(e.response.status_code)
                + " connecting to SolarEdge Portal to fetch sensor value",
            )

        jsondata = r.json()
        return jsondata

    def getBestJsonSet(self, jsondata, dt):
        # get the json data that matches best based on dt

        bestjson = jsondata["current"]
        dif = abs(bestjson["dt"] - dt)

        for section in ["hourly", "daily"]:
            for subset in jsondata[section]:
                cmp = abs(subset["dt"] - dt)
                if (dif == 0) or (cmp < dif):
                    dif = cmp
                    bestjson = subset

        return bestjson

    def update(self):

        month = int(time.strftime("%m"))
        dt = int(time.time())
        if (int(time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from OpenWeatherMap inverter.
            tmp = self.getOpenWeatherMapData()
            if tmp:
                self.LastJson = tmp
                # Update last fetch time
                if self.fetchFailed is not True:
                    self.lastFetch = int(time.time())

        if self.LastJson:
            try:
                subset = self.getBestJsonSet(self.LastJson, dt)
                sunrise = self.LastJson["current"]["sunrise"]
                sunset = self.LastJson["current"]["sunset"]
                clouds = subset["clouds"]
                temp = subset["temp"]

                logger.info("OpenWeatherMap response/subset: " + str(subset))

                # it's night time!
                if (dt < sunrise) or (dt > sunset):
                    self.generatedW = 0
                    logger.info("OpenWeatherMap said it's Nighttime -> 0 kw")
                else:
                    # modifier based on date time
                    midday = int(sunrise + ((sunset - sunrise) / 2))
                    if dt < midday:
                        mod_day = (1 / (midday - sunrise)) * (dt - sunrise)
                    else:
                        mod_day = (1 / (midday - sunrise)) * (
                            midday - (dt - midday) - sunrise
                        )
                    if mod_day > 0.9:
                        mod_day = 1
                    elif mod_day < 0.2:
                        mod_day = 0.2

                    # modifier based on clouds, the /3 was done to improve results...cuz clouds with e.g. 70% almost always gave back 100% kw anyway
                    mod_cloud = 1 - (clouds / 100 / 3)

                    # a temperature above 87° fahrenheit (or 31° celsius) will reduce effeciency by 1% each degree
                    # at least thats what a paper suggested
                    if temp > 31:
                        mod_temp = 1 - ((temp - 31) / 100)
                        if mod_temp > 0.5:
                            # limit this modification by 0.5 maximum
                            mod_temp = 0.5
                    else:
                        mod_temp = 1

                    # other ideas...
                    # - reduce on snow
                    # - use uvi value to calculate another modifier...though needs monitoring a longer range
                    # - reduce on fog
                    # - use none linear sunrise/sunset -> midday but gausian algo here

                    self.generatedW = (
                        self.PeakKW[month - 1] * mod_day * mod_cloud * mod_temp * 1000
                    )
                    logger.info(
                        "peak: "
                        + str(self.PeakKW[month - 1])
                        + ", mod_cloud: "
                        + str(mod_cloud)
                        + ", mod_day:"
                        + str(mod_day)
                        + ", mod_temp:"
                        + str(mod_temp)
                    )

            except (KeyError, TypeError) as e:
                logger.log(logging.INFO4, "Exception during parsing OpenWeatherMapData")
                logger.debug(e)

            return True
        else:
            # Cache time has not elapsed since last fetch, serve from cache.
            return False
