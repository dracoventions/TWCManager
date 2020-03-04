# Tesla Powerwall 2

class TeslaPowerwall2:

  import requests
  import time
  import urllib3
  import json as json

  batteryLevel    = 100
  cacheTime       = 10
  config          = None
  configConfig    = None
  configPowerwall = None
  consumedW       = 0
  debugLevel      = 0
  fetchFailed     = False
  generatedW      = 0
  gridStatus      = False
  importW         = 0
  exportW         = 0
  minSOE          = 90
  operatingMode   = ''
  reservePercent  = 100
  lastFetch       = 0
  password        = None
  serverIP        = None
  serverPort      = 443
  status          = False
  timeout         = 10
  token           = None
  tokenProvider   = None
  tokenTimeout    = None
  voltage         = 0

  def __init__(self, master):
    self.config            = master.config
    try:
      self.configConfig    = self.config['config']
    except KeyError:
      self.configConfig    = {}
    try:
      self.configPowerwall = self.config['sources']['Powerwall2']
    except KeyError:
      self.configPowerwall = {}
    self.debugLevel        = self.configConfig.get('debugLevel', 0)
    self.status            = self.configPowerwall.get('enabled', False)
    self.serverIP          = self.configPowerwall.get('serverIP', None)
    self.serverPort        = self.configPowerwall.get('serverPort','443')
    self.password          = self.configPowerwall.get('password', None)
    self.minSOE            = self.configPowerwall.get('minBatteryLevel', 90)
    if self.status and self.debugLevel < 11:
      # PW uses self-signed certificates; squelch warnings
      self.urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("Powerwall2: (" + str(minlevel) + ") " + message)

  def doPowerwallLogin(self):
    # If we have password authentication configured, this function will submit
    # the login details to the Powerwall API, and get an authentication token.
    # If we already have an authentication token, we just use that.
    if (self.password is not None):
      if (self.token is None or self.tokenTimeout < self.time.time()):
        self.debugLog(6, "Logging in to Powerwall API")
        headers = {
          "Content-Type": "application/json"
        }
        data = {
          "username": "customer",
          "password": self.password,
          "force_sm_off": False
        }
        url = "https://" + self.serverIP + ":" + self.serverPort
        url += "/api/login/Basic"
        try:
          req = self.requests.post(url, headers=headers, json = data, timeout=self.timeout, verify=False)
        except self.requests.exceptions.ConnectionError as e:
          self.debugLog(4, "Error connecting to Tesla Powerwall 2 for API login")
          self.debugLog(10, str(e))
          return False

        rjson = self.json.loads(req.text)
        self.token = rjson['token']
        self.tokenProvider = rjson['provider']

        # Time out token after one hour
        self.tokenTimeout = (self.time.time() + (60 * 60))
        self.debugLog(4, "Powerwall2 API Login returned token " + str(rjson['token']))

        # After authentication, start Powerwall
        # If we don't do this, the Powerwall will stop working after login
        self.startPowerwall()

      else:

        self.debugLog(6, "Powerwall2 API token " + str(self.token) + " still valid for " + str(self.tokenTimeout - self.time.time()) + " seconds.")

  def getConsumption(self):

    if (not self.status):
      self.debugLog(10, "Powerwall2 EMS Module Disabled. Skipping getConsumption")
      return 0

    # Perform updates if necessary
    self.update()

    # Return consumption value
    return float(self.consumedW)

  def getGeneration(self):

    if (not self.status):
      self.debugLog(10, "Powerwall2 EMS Module Disabled. Skipping getGeneration")
      return 0

    # Perform updates if necessary
    self.update()

    if ( self.batteryLevel < self.minSOE ):
      # Battery is below threshold; keep all generation for PW charging
      self.debugLog(5, "Powerwall2 energy level below target. Skipping getGeneration")
      return 0

    # Return generation value
    return float(self.generatedW)

  def getPWJson(self, path):
    # Fetch the specified URL from Powerwall and return the data
    self.fetchFailed = False

    # Get a login token, if password authentication is enabled
    self.doPowerwallLogin()

    url = "https://" + self.serverIP + ":" + self.serverPort + path
    headers = {}

    # Send authentication token if password authentication is enabled
    if self.password is not None:
      if self.tokenProvider == "Basic":
        headers['Authorization'] = "Bearer " + self.token
      else:
        self.debugLog(1, "Error: Powerwall password is set, but no token method matches.")
        self.debugLog(1, "Token method reported by Powerwall is " + str(self.tokenProvider))

    try:
      r = self.requests.get(url, headers = headers, timeout=self.timeout, verify=False)
      r.raise_for_status()
    except self.requests.exceptions.ConnectionError as e:
        self.debugLog(4, "Error connecting to Tesla Powerwall 2 to fetch " + path)
        self.debugLog(10, str(e))
        self.fetchFailed = True
        return False

    return r.json()

  def getPWValues(self):
    return self.getPWJson("/api/meters/aggregates")

  def getSOE(self):
    return self.getPWJson("/api/system_status/soe")

  def getOperation(self):
    return self.getPWJson("/api/operation")

  def startPowerwall(self):
    # This function will instruct the powerwall to run.
    # This is needed after getting a login token for v1.15 and above

    # Get a login token, if password authentication is enabled
    self.doPowerwallLogin()

    url = "https://" + self.serverIP + ":" + self.serverPort
    url += "/api/sitemaster/run"
    headers = {}

    # Send authentication token if password authentication is enabled
    if self.password is not None:
      if self.tokenProvider == "Basic":
        headers['Authorization'] = "Bearer " + self.token
      else:
        self.debugLog(1, "Error: Powerwall password is set, but no token method matches.")
        self.debugLog(1, "Token method reported by Powerwall is " + str(self.tokenProvider))

    try:
        r = self.requests.get(url, headers = headers, timeout=self.timeout, verify=False)
    except self.requests.exceptions.ConnectionError as e:
        self.debugLog(4, "Error instructing Tesla Powerwall 2 to start")
        self.debugLog(10, str(e))
        return False

  def update(self):

    if ((int(self.time.time()) - self.lastFetch) > self.cacheTime):
      # Cache has expired. Fetch values from Powerwall.

      value = self.getPWValues()

      if (value):
        self.generatedW = float(value['solar']['instant_power'])
        self.consumedW = float(value['load']['instant_power'])

        # Determine grid status from "site" (grid) frequency
        if (int(value['site']['frequency']) == 0):
          self.gridStatus = False
        else:
          self.gridStatus = True

        self.voltage = int(value['site']['instant_average_voltage'])
      else:
        # Fetch failed to obtain values
        self.fetchFailed = True

      value = self.getSOE()

      if (value):
        self.batteryLevel = float(value['percentage'])
      else:
        self.fetchFailed = True

      value = self.getOperation()

      if (value):
        self.operatingMode = value['mode']
        self.reservePercent = value['backup_reserve_percent']
      else:
        self.fetchFailed = True

      # Update last fetch time
      if (self.fetchFailed is not True):
        self.lastFetch = int(self.time.time())

      return True
    else:
      # Cache time has not elapsed since last fetch, serve from cache.
      return False
