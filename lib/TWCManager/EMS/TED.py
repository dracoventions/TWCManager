# The Energy Detective (TED)

class TED:

    # I check solar panel generation using an API exposed by The
    # Energy Detective (TED). It's a piece of hardware available
    # at http://www.theenergydetective.com

  import requests
  import time

  cacheTime   = 60
  consumedW   = 0
  debugLevel  = 0
  fetchFailed = False
  generatedW  = 0
  importW     = 0
  exportW     = 0
  lastFetch   = 0
  serverIP    = None
  serverPort  = 80
  status      = False
  timeout     = 10
  voltage     = 0

  def __init__(self, debugLevel, config):
    self.debugLevel  = debugLevel
    self.status      = config.get('enabled', False)
    self.serverIP    = config.get('serverIP', None)
    self.serverPort  = config.get('serverPort','80')

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("Fronius: (" + str(minlevel) + ") " + message)

  def getConsumption(self):

    if (not self.status):
      self.debugLog(10, "TED EMS Module Disabled. Skipping getConsumption")
      return 0

    # Perform updates if necessary
    self.update()

    # Return consumption value. Fronius consumption is either negative
    # (export to grid) or positive (import from grid). We add generation
    # value to make it the delta between this and current consumption
    if ((self.consumedW < 0) or (self.consumedW > 0)):
      return float(self.generatedW + self.consumedW)
    else:
      return float(0)

  def getGeneration(self):

    if (not self.status):
      self.debugLog(10, "TED EMS Module Disabled. Skipping getGeneration")
      return 0

    # Perform updates if necessary
    self.update()

    # Return generation value
    return float(self.generatedW)

  def getTEDValue(self, url):

    # Fetch the specified URL from the Fronius Inverter and return the data
    self.fetchFailed = False

    try:
        r = self.requests.get(url, timeout=self.timeout)
    except self.requests.exceptions.ConnectionError as e:
        self.debugLog(4, "Error connecting to Fronius Inverter to fetch sensor value")
        self.debugLog(10, str(e))
        self.fetchFailed = True
        return False

    r.raise_for_status()
    return r

  def update(self):

    if ((int(self.time.time()) - self.lastFetch) > self.cacheTime):
      # Cache has expired. Fetch values from HomeAssistant sensor.

      url = "http://" + self.serverIP + ":" + self.serverPort
      url = url + "/history/export.csv?T=1&D=0&M=1&C=1"

      value = self.getTEDValue(url)
      m = re.search(b'^Solar,[^,]+,-?([^, ]+),', value, re.MULTILINE)

      if(m):
        self.generatedW = int(float(m.group(1)) * 1000)

      # Update last fetch time
      if (self.fetchFailed is not True):
        self.lastFetch = int(self.time.time())

      return True
    else:
      # Cache time has not elapsed since last fetch, serve from cache.
      return False
