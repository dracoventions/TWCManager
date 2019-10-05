# HomeAssistant Status Output
# Publishes the provided sensor key and value pair to a HomeAssistant instance

class HASSStatus:

  import requests
  
  apiKey       = None
  debugLevel   = 0
  status       = False
  serverIP     = None
  serverPort   = 8123
  timeout      = 2
  
  def __init__(self, debugLevel, status, serverIP, serverPort, apiKey):
    self.status      = status
    self.serverIP    = serverIP
    self.serverPort  = serverPort
    self.apiKey      = apiKey
    self.debugLevel  = debugLevel

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("debugLog: (" + str(minlevel) + ") " + message)

  def setStatus(self, twcid, key, value):
    sensor = "sensor.twcmanager_" + str(twcid.decode("utf-8")) + "_" + key

    if (self.status):
      url = "http://" + self.serverIP + ":" + self.serverPort 
      url = url + "/api/states/" + sensor
      headers = {
          'Authorization': 'Bearer ' + self.apiKey,
          'content-type': 'application/json'
      }

      try:
          self.debugLog(8, "Sending POST request to HomeAssistant for sensor " + sensor + "(value " + str(value) + ").")
          self.requests.post(url, json={"state":value}, timeout=self.timeout, headers=headers)
      except self.requests.exceptions.ConnectionError as e:
          self.debugLog(4, "Error connecting to HomeAssistant to publish sensor values")
          self.debugLog(10, str(e))
          return False

