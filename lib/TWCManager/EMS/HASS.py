class HASS:

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
    self.status                = config,get('enabled', False)
    self.serverIP              = config.get('serverIP', None)
    self.serverPort            = config.get('serverPort', 8123)
    self.apikey                = config.get('apiKey',None)
    self.debugLevel            = debugLevel
    self.hassEntityConsumption = config.get('hassEntityConsumption', None)
    self.hassEntityGeneration  = config.get('hassEntityGeneration', None)
    
  def getConsumption(self):
    
    if (not self.status):
      return 0
    
    # Perform updates if necessary
    self.update()
    
    # Return consumption value
    return self.consumedW

  def getGeneration(self):
    
    if (not self.status):
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
        httpResponse = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError as e: 
        print("Error connecting to HomeAssistant")
        print(e)
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
          testvalue = getAPIValue(self.hassEntityConsumption)
          print("TEST TEST TEST TEST " + testvalue)

      if (self.hassEntityGeneration):
          testvalue = getAPIValue(self.hassEntityGeneration)
          print("TEST TEST TEST TEST " + testvalue)

      # Update last fetch time
      self.lastFetch = int(self.time.time())
      return True
    else:
      # Cache time has not elapsed since last fetch, serve from cache.
      return
