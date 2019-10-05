class HASS:

  # HomeAssistant EMS Module
  # Fetches Consumption and Generation details from HomeAssistant
  
  import requests
  import time
  
  apiKey                = None
  cacheTime             = 60
  consumedW             = 0
  debugLevel            = 0
  generatedW            = 0
  hassEntityConsumption = None
  hassEntityGeneration  = None
  lastFetch             = 0
  status                = False
  serverIP              = None
  serverPort            = 8123
  timeout               = 2
  
  def __init__(self, debugLevel, config):
    self.status                = config.get('enabled', False)
    self.serverIP              = config.get('serverIP', None)
    self.serverPort            = config.get('serverPort', 8123)
    self.apiKey                = config.get('apiKey', None)
    self.debugLevel            = debugLevel
    self.hassEntityConsumption = config.get('hassEntityConsumption', None)
    self.hassEntityGeneration  = config.get('hassEntityGeneration', None)

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("debugLog: (" + str(minlevel) + ") " + message)
      
  def getConsumption(self):
    
    if (not self.status):
      self.debugLog(10, "HASS EMS Module Disabled. Skipping getConsumption")
      return 0
    
    # Perform updates if necessary
    self.update()
    
    # Return consumption value
    return self.consumedW

  def getGeneration(self):
    
    if (not self.status):
      self.debugLog(10, "HASS EMS Module Disabled. Skipping getConsumption")
      return 0
    
    # Perform updates if necessary
    self.update()
    
    # Return generation value
    return self.generatedW
  
  def getAPIValue(self, entity):
    url = "http://" + self.serverIP + ":" + self.serverPort + "/api/states/" + entity
    headers = {
        'Authorization': 'Bearer ' + self.apiKey,
        'content-type': 'application/json'
    }

    try:
        httpResponse = self.requests.get(url, headers=headers)
    except self.requests.exceptions.ConnectionError as e: 
        self.debugLog(4, "Error connecting to HomeAssistant to publish sensor values")
        self.debugLog(10, str(e))
        return 0

    jsonResponse = httpResponse.json() if httpResponse and httpResponse.status_code == 200 else None

    if jsonResponse:
        return jsonResponse["state"]
    else:
        return None

  def update(self):
    # Update
    if ((int(self.time.time()) - self.lastFetch) > self.cacheTime):
      # Cache has expired. Fetch values from HomeAssistant sensor.
            
      if (self.hassEntityConsumption):
          apivalue = self.getAPIValue(self.hassEntityConsumption)
          self.debugLog(10, "HASS getConsumption returns " + str(apivalue))
          self.consumedW = float(apivalue)
      else:
          self.debugLog(10, "HASS Consumption Entity Not Supplied. Not Querying")

      if (self.hassEntityGeneration):
          apivalue = self.getAPIValue(self.hassEntityGeneration)
          self.debugLog(10, "HASS getGeneration returns " + str(apivalue))
          self.generatedW = float(apivalue)
      else:
          self.debugLog(10, "HASS Generation Entity Not Supplied. Not Querying")

      # Update last fetch time
      self.lastFetch = int(self.time.time())
      return True
    else:
      # Cache time has not elapsed since last fetch, serve from cache.
      return
