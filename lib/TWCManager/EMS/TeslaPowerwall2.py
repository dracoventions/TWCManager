# Tesla Powerwall 2

class TeslaPowerwall2:

  import requests
  import time

  cacheTime   = 60
  config      = None
  consumedW   = 0
  debugLevel  = 0
  fetchFailed = False
  generatedW  = 0
  importW     = 0
  exportW     = 0
  lastFetch   = 0
  password    = None
  serverIP    = None
  serverPort  = 443
  status      = False
  timeout     = 10
  voltage     = 0

  def __init__(self, master):
    self.config      = master.config
    self.debugLevel  = self.config.get('debugLevel', 0)
    self.status      = self.config.get('enabled', False)
    self.serverIP    = self.config.get('serverIP', None)
    self.serverPort  = self.config.get('serverPort','443')
    self.password    = self.config.get('password', None)

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("Powerwall2: (" + str(minlevel) + ") " + message)

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

    # Return generation value
    return float(self.generatedW)

  def getPWValues(self):

    # Fetch the specified URL from Powerwall and return the data
    self.fetchFailed = False

    url = "https://" + self.serverIP + ":" + self.serverPort
    url += "/api/meters/aggregates"

    try:
        r = self.requests.get(url, timeout=self.timeout, verify=False)
    except self.requests.exceptions.ConnectionError as e:
        self.debugLog(4, "Error connecting to Tesla Powerwall 2 to fetch solar data")
        self.debugLog(10, str(e))
        self.fetchFailed = True
        return False

    r.raise_for_status()
    return r.json()

  def update(self):

    if ((int(self.time.time()) - self.lastFetch) > self.cacheTime):
      # Cache has expired. Fetch values from Powerwall.

      value = self.getPWValues()

      if (value):
        self.generatedW = float(value['solar']['instant_power'])
        self.consumedW = float(value['load']['instant_power'])
      else:
        # Fetch failed to obtain values
        self.fetchFailed = True

      # Update last fetch time
      if (self.fetchFailed is not True):
        self.lastFetch = int(self.time.time())

      return True
    else:
      # Cache time has not elapsed since last fetch, serve from cache.
      return False
