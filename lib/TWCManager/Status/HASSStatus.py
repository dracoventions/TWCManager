# HomeAssistant Status Output
# Publishes the provided sensor key and value pair to a HomeAssistant instance

from termcolor import colored
from ww import f

class HASSStatus:

  import time
  import requests

  apiKey           = None
  config           = None
  configConfig     = None
  configHASS       = None
  debugLevel       = 0
  master           = None
  msgRate          = {}
  msgRatePerSensor = 60
  status           = False
  serverIP         = None
  serverPort       = 8123
  timeout          = 2

  def __init__(self, master):
    self.config         = master.config
    self.master         = master
    try:
      self.configConfig = self.config['config']
    except KeyError:
      self.configConfig = {}
    try:
      self.configHASS   = self.config['status']['HASS']
    except KeyError:
      self.configHASS   = {}
    self.status         = self.configHASS.get('enabled', False)
    self.serverIP       = self.configHASS.get('serverIP', None)
    self.serverPort     = self.configHASS.get('serverPort', 8123)
    self.apiKey         = self.configHASS.get('apiKey', None)
    self.debugLevel     = self.configConfig.get('debugLevel', 0)

  def setStatus(self, twcid, key_underscore, key_camelcase, value):

    # Format TWCID nicely
    twident = None
    if (len(twcid) == 2):
      twident = "%02X%02X" % (twcid[0], twcid[1])
    else:
      twident = str(twcid.decode("utf-8"))

    sensor = "sensor.twcmanager_" + str(twident) + "_" + key_underscore

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
          self.master.debugLog(8, "HASSStatus", "Sending POST request to HomeAssistant for sensor " + sensor + "(value " + str(value) + ").")
          self.requests.post(url, json={"state":value}, timeout=self.timeout, headers=headers)
      except self.requests.exceptions.ConnectionError as e:
        self.master.debugLog(4, "HASSStatus", "Error connecting to HomeAssistant to publish sensor values")
        self.master.debugLog(10, "HASSStatus", str(e))
        return False
      except self.requests.exceptions.ReadTimeout as e:
        self.master.debugLog(4, "HASSStatus", "Error connecting to HomeAssistant to publish sensor values")
        self.master.debugLog(10, "HASSStatus", str(e))
        return False
      except Exception as e:
        self.master.debugLog(4, "HASSStatus", "Error during publishing HomeAssistant sensor values")
        self.master.debugLog(10, "HASSStatus", str(e))
        return False
