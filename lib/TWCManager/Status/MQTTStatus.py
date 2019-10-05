# MQTT Status Output
# Publishes the provided key and value pair to the provided topic prefix

class MQTTStatus:

  import paho.mqtt.client as mqtt
  
  debugLevel    = 0
  status        = False
  serverIP      = None
  topicPrefix   = None
  
  def __init__(self, debugLevel, status, serverIP, topicPrefix):
    self.debugLevel  = debugLevel
    self.status      = status
    self.serverIP    = serverIP
    self.topicPrefix = topicPrefix
    
  def setStatus(self, twcid, key, value):
    if (self.status):
      try:
        client = self.mqtt.Client("P1")
        client.connect(self.serverIP)
      except ConnectionRefusedError as e:
        print("Error connecting to MQTT Broker")
        print(e)
        return false

      try:
        client.publish(self.topicPrefix+ "/" + str(twcid.decode("utf-8")) + "/" + key, payload=value)
      except e:
        print("Error publishing MQTT Topic Status")
        print(e)
        return false

      client.disconnect()
