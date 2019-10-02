# MQTT Status Output

class MQTTStatus:

  def __init__(self, serverIP, topicPrefix):
    self.serverIP = serverIP
    self.topicPrefix = topicPrefix
    
  def setStatus(key, value):
    if (self.mqttBrokerIP):
      publish.single(self.topicPrefix+"/"+key, payload=value, hostname=self.serverIP
