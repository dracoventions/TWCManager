# MQTT Status Output

class MQTTStatus:

  import paho.mqtt.client as mqtt
  
  status = false
  serverIP = None
  topicPrefix = None
  
  def __init__(self, status, serverIP, topicPrefix):
    self.status = status
    self.serverIP = serverIP
    self.topicPrefix = topicPrefix
    
  def setStatus(key, value):
    if (self.status):
        client = mqtt.Client("P1")
        client.connect(self.serverIP)
        client.publish(self.topicPrefix+"/"+key, payload=value)
        client.disconnect()
