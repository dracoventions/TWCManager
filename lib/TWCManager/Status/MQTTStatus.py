# MQTT Status Output
# Publishes the provided key and value pair to the provided topic prefix

class MQTTStatus:

  import paho.mqtt.client as mqtt
  
  status = False
  serverIP = None
  topicPrefix = None
  
  def __init__(self, status, serverIP, topicPrefix):
    self.status = status
    self.serverIP = serverIP
    self.topicPrefix = topicPrefix
    
  def setStatus(self, twcid, key, value):
    if (self.status):
        client = mqtt.Client("P1")
        client.connect(self.serverIP)
        client.publish(self.topicPrefix+ "/" + twcid + "/" + key, payload=value)
        client.disconnect()
