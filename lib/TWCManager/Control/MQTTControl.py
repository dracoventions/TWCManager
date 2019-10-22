class MQTTControl:

  import paho.mqtt.client as mqtt
  import _thread

  brokerIP        = None
  brokerPort      = 1883
  client          = None
  config          = None
  connectionState = 0
  debugLevel      = 0
  master          = None
  password        = None
  status          = False
  serverTLS       = False
  topicPrefix     = None
  username        = None
  
  def __init__(self, master):
    self.config      = master.config
    self.debugLevel  = self.config.get('debugLevel', 0)
    self.status      = self.config.get('enabled', False)
    self.brokerIP    = self.config.get('brokerIP', None)
    self.master      = master
    self.topicPrefix = self.config.get('topicPrefix', None)
    self.username    = self.config.get('username', None)
    self.password    = self.config.get('password', None)

    # Subscribe to the specified topic prefix, and process incoming messages
    # to determine if they represent control messages
    self.debugLog(10, "Attempting to Connect")
    if (self.brokerIP):
      self.client = self.mqtt.Client("MQTTCtrl")
      if (self.username and self.password):
        self.client.username_pw_set(self.username, self.password)
      self.client.on_connect = self.mqttConnect
      self.client.on_message = self.mqttMessage
      self.client.on_subscribe = self.mqttSubscribe
      try:
        self.client.connect_async(self.brokerIP, port=self.brokerPort, keepalive=30)
      except ConnectionRefusedError as e:
        self.debugLog(4, "Error connecting to MQTT Broker")
        self.debugLog(10, str(e))
        return False
      except OSError as e:
        self.debugLog(4, "Error connecting to MQTT Broker")
        self.debugLog(10, str(e))
        return False

      self.connectionState = 1
      self.client.loop_start()

    else:
      self.debugLog(4, "MQTTControl enabled but no brokerIP specified.")

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("MQTTControl: (" + str(minlevel) + ") " + message)
 
  def mqttConnect(self, client, userdata, flags, rc):
    self.debugLog(5, "MQTT Connected.")
    self.debugLog(5, "Subscribe to " + self.topicPrefix + "/#")
    res = self.client.subscribe(self.topicPrefix + "/#", qos=0)
    self.debugLog(5, "Res: " + str(res))

  def mqttMessage(self, client, userdata, message):

    if (message.topic == self.topicPrefix + "/control/chargeNow"):
      self.debugLog(3, "MQTT Message called chargeNow")
      self.master.setChargeNowAmps(12)
      self.master.setChargeNowTimeEnd(60*60*24)

    if (message.topic == self.topicPrefix + "/control/chargeNowEnd"):
      self.debugLog(3, "MQTT Message called chargeNowEnd")
      self.master.resetChargeNowAmps()

    if (message.topic == self.topicPrefix + "/control/stop"):
      self.debugLog(3, "MQTT Message called Stop")
      self._thread.interrupt_main()

  def mqttSubscribe(self, client, userdata, mid, granted_qos):
    self.debugLog(1, "Subscribe operation completed with mid " + str(mid))
