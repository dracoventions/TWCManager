# MQTT Status Output
# Publishes the provided key and value pair to the provided topic prefix

class MQTTStatus:

  import time
  import paho.mqtt.client as mqtt
  
  connectionState = 0
  debugLevel      = 0
  msgQueue        = []
  msgQueueBuffer  = []
  msgQueueMax     = 16
  msgRate         = {}
  msgRatePerTopic = 60
  status          = False
  serverIP        = None
  topicPrefix     = None
  
  def __init__(self, debugLevel, status, serverIP, topicPrefix):
    self.debugLevel  = debugLevel
    self.status      = status
    self.serverIP    = serverIP
    self.topicPrefix = topicPrefix
    
  def setStatus(self, twcid, key, value):
    if (self.status):

      topic = self.topicPrefix+ "/" + str(twcid.decode("utf-8"))
      topic = topic + "/" + key

      # Perform rate limiting first (as there are some very chatty topics).
      # For each message that comes through, we take the topic name and check
      # when we last sent a message. If it was less than msgRatePerTopic
      # seconds ago, we dampen it.
      if (topic in self.msgRate): 
        if ((self.time.time() - self.msgRate[topic]) < self.msgRatePerTopic):
          return True
        else:
          self.msgRate[topic] = self.time.time()
      else:
        self.msgRate[topic] = self.time.time()

      # Now, we push the message that we'd like to send into the
      # list of messages to be published once a connection is established
      msg = { "topic": topic, "payload": value }
      self.msgQueue.append(msg.copy())

      # If msgQueue size exceeds msgQueueMax, trim the list size
      # This will discard MQTT messages in environments where the MQTT
      # broker cannot accept the rate of MQTT messages sent
      if (len(self.msgQueue) > (self.msgQueueMax + 8)):
        del self.msgQueue[:self.msgQueueMax]

      # Now, we attempt to establish a connection to the MQTT broker
      if (self.connectionState == 0):
        try:
          client = self.mqtt.Client("P1")
          client.on_connect = self.mqttConnected
          client.connect_async(self.serverIP)
          self.connectionState = 1
          client.loop_start()
        except ConnectionRefusedError as e:
          print("Error connecting to MQTT Broker")
          print(e)
          return false

  def mqttConnected(self, client, userdata, flags, rc):
    # This callback function is called once the MQTT client successfully
    # connects to the MQTT server. It will then publish all queued messages
    # to the server, and then disconnect.

    self.msgQueueBuffer = self.msgQueue.copy()
    self.msgQueue.clear()

    for msg in self.msgQueueBuffer:
      try:
        client.publish(msg[topic], payload=msg[payload])
      except e:
        print("Error publishing MQTT Topic Status")
        print(e)
        return false

    client.loop_stop()
    self.connectionState = 0
    client.disconnect()
