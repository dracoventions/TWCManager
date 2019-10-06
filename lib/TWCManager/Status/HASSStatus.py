# HomeAssistant Status Output
# Publishes the provided sensor key and value pair to a HomeAssistant instance

class HASSStatus:

  import time
  import requests
  
  apiKey           = None
  debugLevel       = 0
  msgRate          = {}
  msgRatePerSensor = 60
  status       = False
  serverIP     = None
  serverPort   = 8123
  timeout      = 2
  
  def __init__(self, debugLevel, config):
    self.status      = config.get('enabled', False)
    self.serverIP    = config.get('serverIP', None)
    self.serverPort  = config.get('serverPort', 8123)
    self.apiKey      = config.get('apiKey', None)
    self.debugLevel  = debugLevel

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("debugLog: (" + str(minlevel) + ") " + message)

  def setStatus(self, twcid, key, value):
    sensor = "sensor.twcmanager_" + str(twcid.decode("utf-8")) + "_" + key

    if (self.status):

      # Perform rate limiting first (as there are some very chatty topics).
      # For each message that comes through, we take the sensor name and check
      # when we last updated it. If it was less than msgRatePerSensor
      # seconds ago, we dampen it.
      if (sensor in self.msgRate):
        if ((self.time.time() - self.msgRate[sensor]) < self.msgRatePerSensor):
          return True
        else:
          self.msgRate[sensor] = self.time.time()
      else:
        self.msgRate[sensor] = self.time.time()

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
      except self.requests.exceptions.ReadTimeout as e:
          self.debugLog(4, "Error connecting to HomeAssistant to publish sensor values")
          self.debugLog(10, str(e))
          return False
      except Exception as e:
          self.debugLog(4, "Error during publishing HomeAssistant sensor values")
          self.debugLog(10, str(e))
          return False
