class HASS:

  import requests
  
  apiKey = None
  debugLevel = 0
  status = False
  serverIP = None
  serverPort = 8123
  timeout = 2
  
  def __init__(self, status, serverIP, serverPort):
    self.status = status
    self.serverIP = serverIP
    self.serverPort = serverPort

