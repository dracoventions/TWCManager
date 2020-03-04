#! /usr/bin/python3

from lib.TWCManager.TWCSlave import TWCSlave
from datetime import datetime
import json
import os.path
import queue
import serial
import threading
import time

class TWCMaster:

  active_policy       = None
  backgroundTasksQueue = queue.Queue()
  backgroundTasksCmds = {}
  backgroundTasksLock = threading.Lock()
  carapi              = None
  charge_policy       = [
    # The first policy table entry is for chargeNow. This will fire if
    # chargeNowAmps is set to a positive integer and chargeNowTimeEnd
    # is less than or equal to the current timestamp
    { "name": "Charge Now",
      "match": [ "settings.chargeNowAmps", "settings.chargeNowTimeEnd", "settings.chargeNowTimeEnd" ],
      "condition": [ "gt", "gt", "gt" ],
      "value": [ 0, 0, "now" ],
      "charge_amps": "settings.chargeNowAmps" },

    # If we are within Track Green Energy schedule, charging will be
    # performed based on the amount of solar energy being produced.
    # Don't bother to check solar generation before 6am or after
    # 8pm. Sunrise in most U.S. areas varies from a little before
    # 6am in Jun to almost 7:30am in Nov before the clocks get set
    # back an hour. Sunset can be ~4:30pm to just after 8pm.
    { "name": "Track Green Energy",
      "match": [ "tm_hour", "tm_hour", "settings.hourResumeTrackGreenEnergy" ],
      "condition": [ "gt", "lte", "lte" ],
      "value": [ 6, 20, "tm_hour" ],
      "charge_amps": "getMaxAmpsToDivideGreenEnergy()",
      "background_task": "checkGreenEnergy" },

    # Check if we are currently within the Scheduled Amps charging schedule.
    # If so, charge at the specified number of amps.
    { "name": "Scheduled Charging",
      "match": [ "checkScheduledCharging()" ],
      "condition": [ "eq" ],
      "value": [ 1 ],
      "charge_amps": "settings.scheduledAmpsMax" },

      # If all else fails (ie no other policy match), we will charge at
      # nonScheduledAmpsMax
    { "name": "Non Scheduled Charging",
      "match": [ "none" ],
      "condition": [ "none" ],
      "value": [ 0 ],
      "charge_amps": "settings.nonScheduledAmpsMax" }
  ]

  config              = None
  consumptionValues   = {}
  debugLevel          = 0
  generationValues    = {}
  hassstatus          = None
  lastPolicyCheck     = 0
  lastTWCResponseMsg  = None
  masterTWCID         = ''
  maxAmpsToDivideAmongSlaves = 0
  modules             = {}
  mqttstatus          = None
  overrideMasterHeartbeatData = b''
  policyCheckInterval = 30
  protocolVersion     = 2
  ser                 = None
  settings            = {
    'chargeNowAmps'            : 0,
    'chargeStopMode'           : "1",
    'chargeNowTimeEnd'         : 0,
    'homeLat'                  : 10000,
    'homeLon'                  : 10000,
    'hourResumeTrackGreenEnergy' : -1,
    'kWhDelivered'             : 119,
    'nonScheduledAmpsMax'      : 0,
    'respondToSlaves'          : 1,
    'scheduledAmpsDaysBitmap'  : 0x7F,
    'scheduledAmpsEndHour'     : -1,
    'scheduledAmpsMax'         : 0,
    'scheduledAmpsStartHour'   : -1
  }
  slaveHeartbeatData = bytearray([0x01,0x0F,0xA0,0x0F,0xA0,0x00,0x00,0x00,0x00])
  slaveTWCs           = {}
  slaveTWCRoundRobin  = []
  spikeAmpsToCancel6ALimit = 16
  subtractChargerLoad = False
  teslaLoginAskLater  = False
  timeLastTx          = 0
  TWCID               = None

# TWCs send a seemingly-random byte after their 2-byte TWC id in a number of
# messages. I call this byte their "Sign" for lack of a better term. The byte
# never changes unless the TWC is reset or power cycled. We use hard-coded
# values for now because I don't know if there are any rules to what values can
# be chosen. I picked 77 because it's easy to recognize when looking at logs.
# These shouldn't need to be changed.
  masterSign = bytearray(b'\x77')
  slaveSign = bytearray(b'\x77')

  def __init__(self, TWCID, config, carapi):
    self.carapi     = carapi
    self.config     = config
    self.debugLevel = config['config']['debugLevel']
    self.TWCID      = TWCID
    self.subtractChargerLoad = config['config']['subtractChargerLoad']

    # Override Charge Policy if specified
    config_policy = config.get("policy")
    if (config_policy):
      if (len(config_policy.get("override", [])) > 0):
        # Policy override specified, just ovrrride in place without processing the
        # extensions
        self.charge_policy = config_policy.get("override")
      else:
        # Insert optional policy extensions into policy list
        # After - Inserted before Non-Scheduled Charging
        config_extend = config_policy.get("extend", {})
        if (len(config_extend.get("after", [])) > 0):
          self.charge_policy[3:3] = config_extend.get("after")

        # Before - Inserted after Charge Now
        if (len(config_extend.get("before", [])) > 0):
          self.charge_policy[1:1] = config_extend.get("before")

    # Set the Policy Check Interval if specified
    if (config_policy):
      policy_engine = config_policy.get("engine")
      if (policy_engine):
        if (policy_engine.get('policyCheckInterval')):
          self.policyCheckInterval = policy_engine.get('policyCheckInterval')

    # Register ourself as a module, allows lookups via the Module architecture
    self.registerModule({ "name": "master", "ref": self, "type": "Master" })

    # Connect to serial port
    self.ser = serial.Serial(config['config']['rs485adapter'], config['config']['baud'], timeout=0)

  def addkWhDelivered(self, kWh):
    self.settings['kWhDelivered'] = self.settings.get('kWhDelivered', 0) + kWh

  def addSlaveTWC(self, slaveTWC):
    # Adds the Slave TWC to the Round Robin list
    return self.slaveTWCRoundRobin.append(slaveTWC)

  def checkScheduledCharging(self):

    # Check if we're within the hours we must use scheduledAmpsMax instead
    # of nonScheduledAmpsMax
    blnUseScheduledAmps = 0
    ltNow = time.localtime()

    if(self.getScheduledAmpsMax() > 0 and self.settings.get('scheduledAmpsStartHour', -1) > -1
      and self.getScheduledAmpsEndHour() > -1 and self.getScheduledAmpsDaysBitmap() > 0):
        if(self.settings.get('scheduledAmpsStartHour', -1) > self.getScheduledAmpsEndHour()):
          # We have a time like 8am to 7am which we must interpret as the
          # 23-hour period after 8am or before 7am. Since this case always
          # crosses midnight, we only ensure that scheduledAmpsDaysBitmap
          # is set for the day the period starts on. For example, if
          # scheduledAmpsDaysBitmap says only schedule on Monday, 8am to
          # 7am, we apply scheduledAmpsMax from Monday at 8am to Monday at
          # 11:59pm, and on Tuesday at 12am to Tuesday at 6:59am.
          hourNow = ltNow.tm_hour + (ltNow.tm_min / 60)
          if((hourNow >= self.settings.get('scheduledAmpsStartHour', -1) and (self.getScheduledAmpsDaysBitmap() & (1 << ltNow.tm_wday)))
               or (hourNow < self.getScheduledAmpsEndHour() and (self.getScheduledAmpsDaysBitmap() & (1 << yesterday)))):
             blnUseScheduledAmps = 1
        else:
          # We have a time like 7am to 8am which we must interpret as the
          # 1-hour period between 7am and 8am.
          hourNow = ltNow.tm_hour + (ltNow.tm_min / 60)
          if(hourNow >= self.settings.get('scheduledAmpsStartHour', -1) and hourNow < self.getScheduledAmpsEndHour()
             and (self.getScheduledAmpsDaysBitmap() & (1 << ltNow.tm_wday))):
             blnUseScheduledAmps = 1
    return blnUseScheduledAmps

  def countSlaveTWC(self):
    return int(len(self.slaveTWCRoundRobin))

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("TWCMaster: (" + str(minlevel) + ") " + message)

  def deleteBackgroundTask(self, task):
    del self.backgroundTasksCmds[task['cmd']]

  def doneBackgroundTask(self):
    # task_done() must be called to let the queue know the task is finished.
    # backgroundTasksQueue.join() can then be used to block until all tasks
    # in the queue are done.
    self.backgroundTasksQueue.task_done()

  def getBackgroundTask(self):
    return self.backgroundTasksQueue.get()

  def getBackgroundTasksLock(self):
    self.backgroundTasksLock.acquire()

  def getChargeNowAmps(self):
    # Returns the currently configured Charge Now Amps setting
    chargenow = int(self.settings.get('chargeNowAmps', 0))
    if (chargenow > 0):
      return chargenow
    else:
      return 0

  def getHourResumeTrackGreenEnergy(self):
    return self.settings.get('hourResumeTrackGreenEnergy', -1)

  def getMasterTWCID(self):
    # This is called when TWCManager is in Slave mode, to track the
    # master's TWCID
    return self.masterTWCID

  def gethassstatus(self):
    return self.hassstatus

  def getkWhDelivered(self):
    return self.settings['kWhDelivered']

  def getMaxAmpsToDivideAmongSlaves(self):
    if (self.maxAmpsToDivideAmongSlaves > 0):
      return self.maxAmpsToDivideAmongSlaves
    else:
      return 0

  def getModuleByName(self, name):
    module = self.modules.get(name, None)
    if (module):
      return module['ref']
    else:
      return None

  def getModulesByType(self, type):
    return None

  def getmqttstatus(self):
    return self.mqttstatus

  def getScheduledAmpsDaysBitmap(self):
    return self.settings.get('scheduledAmpsDaysBitmap', 0x7F)

  def getNonScheduledAmpsMax(self):
    nschedamps = int(self.settings.get('nonScheduledAmpsMax', 0))
    if (nschedamps > 0):
      return nschedamps
    else:
      return 0

  def getScheduledAmpsMax(self):
    schedamps = int(self.settings.get('scheduledAmpsMax', 0))
    if (schedamps > 0):
      return schedamps
    else:
      return 0

  def getScheduledAmpsStartHour(self):
    return self.settings.get('scheduledAmpsStartHour', -1)

  def getScheduledAmpsEndHour(self):
    return self.settings.get('scheduledAmpsEndHour', -1)

  def getSlaveSign(self):
    return self.slaveSign

  def getSpikeAmps(self):
    return self.spikeAmpsToCancel6ALimit

  def getTimeLastTx(self):
    return self.timeLastTx

  def deleteSlaveTWC(self, deleteSlaveID):
    for i in range(0, len(self.slaveTWCRoundRobin)):
        if(self.slaveTWCRoundRobin[i].TWCID == deleteSlaveID):
            del self.slaveTWCRoundRobin[i]
            break
    try:
        del self.slaveTWCs[deleteSlaveID]
    except KeyError:
        pass

  def getChargerLoad(self):
    # Calculate in watts the load that the charger is generating so
    # that we can exclude it from the consumption if necessary
    return (self.getTotalAmpsInUse() * 240)

  def getConsumption(self):
    consumptionVal = 0

    for key in self.consumptionValues:
      consumptionVal += float(self.consumptionValues[key])

    if (consumptionVal < 0):
      consumptionVal = 0

    return float(consumptionVal)

  def getFakeTWCID(self):
    return self.TWCID

  def getGeneration(self):
    generationVal = 0

    # Currently, our only logic is to add all of the values together
    for key in self.generationValues:
      generationVal += float(self.generationValues[key])

    if (generationVal < 0):
      generationVal = 0

    return float(generationVal)

  def getGenerationOffset(self):
    # Returns the number of watts to subtract from the solar generation stats
    # This is consumption + charger load if subtractChargerLoad is enabled
    # Or simply consumption if subtractChargerLoad is disabled
    generationOffset = self.getConsumption()
    if (self.subtractChargerLoad):
      generationOffset -= self.getChargerLoad()
    if (generationOffset < 0):
      generationOffset = 0
    return float(generationOffset)

  def getHomeLatLon(self):
    # Returns Lat/Lon coordinates to check if car location is
    # at home
    latlon = []
    latlon[0] = self.settings['homeLat']
    latlon[1] = self.settings['homeLon']
    return latlon

  def getMasterHeartbeatOverride(self):
    return self.overrideMasterHeartbeatData

  def getMaxAmpsToDivideGreenEnergy(self):
    # Watts = Volts * Amps
    # Car charges at 240 volts in North America so we figure
    # out how many amps * 240 = solarW and limit the car to
    # that many amps.

    # Calculate our current generation and consumption in watts
    solarW = float(self.getGeneration() - self.getGenerationOffset())

    # Generation may be below zero if consumption is greater than generation
    if solarW < 0:
        solarW = 0

    # Watts = Volts * Amps
    # Car charges at 240 volts in North America so we figure
    # out how many amps * 240 = solarW and limit the car to
    # that many amps.
    maxAmpsToDivide = (solarW / 240)

    if (maxAmpsToDivide > 0):
      return maxAmpsToDivide
    else:
      return 0

  def getSerial(self):
    return self.ser

  def getSlaveByID(self, twcid):
    return self.slaveTWCs[twcid]

  def getSlaveTWCID(self, twc):
    return self.slaveTWCRoundRobin[twc].TWCID

  def getSlaveTWC(self, id):
    return self.slaveTWCRoundRobin[id]

  def getSlaveTWCs(self):
    # Returns a list of all Slave TWCs
    return self.slaveTWCRoundRobin

  def getTotalAmpsInUse(self):
    # Returns the number of amps currently in use by all TWCs
    totalAmps = 0
    for slaveTWC in self.getSlaveTWCs():
        totalAmps += slaveTWC.reportedAmpsActual
        self.hassstatus.setStatus(slaveTWC.TWCID, "amps_in_use", slaveTWC.reportedAmpsActual)
        self.mqttstatus.setStatus(slaveTWC.TWCID, "ampsInUse", slaveTWC.reportedAmpsActual)

    if(self.config['config']['debugLevel'] >= 10):
        print("Total amps all slaves are using: " + str(totalAmps))
    self.hassstatus.setStatus(bytes("all", 'UTF-8'), "total_amps_in_use", totalAmps)
    self.mqttstatus.setStatus(bytes("all", 'UTF-8'), "totalAmpsInUse", totalAmps)
    return totalAmps

  def hex_str(self, s:str):
    return " ".join("{:02X}".format(ord(c)) for c in s)

  def hex_str(self, ba:bytearray):
    return " ".join("{:02X}".format(c) for c in ba)

  def loadSettings(self):
    # Loads the volatile application settings (such as charger timings,
    # API credentials, etc) from a JSON file

    # Step 1 - Load settings from JSON file
    if (not os.path.exists(self.config['config']['settingsPath'] + '/settings.json')):
      self.settings = {}
      return

    with open(self.config['config']['settingsPath'] + '/settings.json', 'r') as inconfig:
      try:
        self.settings = json.load(inconfig)
      except Exception as e:
        self.debugLog(1, "There was an exception whilst loading settings file " + self.config['config']['settingsPath'] + '/settings.json')
        self.debugLog(1, "Some data may have been loaded. This may be because the file is being created for the first time.")
        self.debugLog(1, "It may also be because you are upgrading from a TWCManager version prior to v1.1.4, which used the old settings file format.")
        self.debugLog(1, "If this is the case, you may need to locate the old config file and migrate some settings manually.")
        self.debugLog(10, str(e))

    # Step 2 - Send settings to other modules
    self.carapi.setCarApiBearerToken(self.settings.get('carApiBearerToken', ''))
    self.carapi.setCarApiRefreshToken(self.settings.get('carApiRefreshToken', ''))
    self.carapi.setCarApiTokenExpireTime(self.settings.get('carApiTokenExpireTime', ''))

  def master_id_conflict():
    # We're playing fake slave, and we got a message from a master with our TWCID.
    # By convention, as a slave we must change our TWCID because a master will not.
    self.TWCID[0] = random.randint(0, 0xFF)
    self.TWCID[1] = random.randint(0, 0xFF)

    # Real slaves change their sign during a conflict, so we do too.
    self.slaveSign[0] = random.randint(0, 0xFF)

    print(time_now() + ": Master's TWCID matches our fake slave's TWCID.  " \
        "Picked new random TWCID %02X%02X with sign %02X" % \
        (self.TWCID[0], self.TWCID[1], self.slaveSign[0]))


  def newSlave(self, newSlaveID, maxAmps):
    try:
        slaveTWC = self.slaveTWCs[newSlaveID]
        # We didn't get KeyError exception, so this slave is already in
        # slaveTWCs and we can simply return it.
        return slaveTWC
    except KeyError:
        pass

    slaveTWC = TWCSlave(newSlaveID, maxAmps, self.config, self.carapi, self)
    self.slaveTWCs[newSlaveID] = slaveTWC
    self.addSlaveTWC(slaveTWC)

    if(self.countSlaveTWC() > 3):
        print("WARNING: More than 3 slave TWCs seen on network.  " \
            "Dropping oldest: " + self.hex_str(self.getSlaveTWCID(0)) + ".")
        self.deleteSlaveTWC(self.getSlaveTWCID(0))

    return slaveTWC

  def num_cars_charging_now(self):

    carsCharging = 0
    for slaveTWC in self.getSlaveTWCs():
        if(slaveTWC.reportedAmpsActual >= 1.0):
            carsCharging += 1
            if(self.config['config']['debugLevel'] >= 10):
                print("BUGFIX: Number of cars charging now: " + str(carsCharging))
            self.hassstatus.setStatus(slaveTWC.TWCID, "cars_charging", carsCharging)
            self.mqttstatus.setStatus(slaveTWC.TWCID, "carsCharging", carsCharging)
    return carsCharging

  def policyValue(self, value):
    # policyValue is a macro to allow charging policy to refer to things
    # such as EMS module values or settings. This allows us to control
    # charging via policy.
    ltNow = time.localtime()

    # If value is "now", substitute with current timestamp
    if (str(value) == "now"):
      return time.time()

    # If value is "tm_hour", substitute with current hour
    if (str(value) == "tm_hour"):
      return ltNow.tm_hour

    # If value refers to a function, execute the function and capture the
    # output
    if (str(value) == "getMaxAmpsToDivideGreenEnergy()"):
      return self.getMaxAmpsToDivideGreenEnergy()
    elif (str(value) == "checkScheduledCharging()"):
      return self.checkScheduledCharging()

    # If value is tiered, split it up
    if strValue.find(".") != -1:
      pieces = str(value).split(".")

      # If value refers to a setting, return the setting
      if pieces[0] == "settings":
        return self.settings.get(pieces[1], 0)
      elif pieces[0] == "config":
        return self.config['config'].get(pieces[1], 0)
      elif pieces[0] == "modules":
        module = None
        if pieces[1] in self.modules:
          module = self.getModuleByName(pieces[1])
          if pieces[2] in vars(module):
            return getattr(module,pieces[2])

    # None of the macro conditions matched, return the value as is
    return value

  def queue_background_task(self, task):

    if(task['cmd'] in self.backgroundTasksCmds):
        # Some tasks, like cmd='charge', will be called once per second until
        # a charge starts or we determine the car is done charging.  To avoid
        # wasting memory queing up a bunch of these tasks when we're handling
        # a charge cmd already, don't queue two of the same task.
        return

    # Insert task['cmd'] in backgroundTasksCmds to prevent queuing another
    # task['cmd'] till we've finished handling this one.
    self.backgroundTasksCmds[task['cmd']] = True

    # Queue the task to be handled by background_tasks_thread.
    self.backgroundTasksQueue.put(task)

  def registerModule(self, module):
    # This function is used during module instantiation to either reference a
    # previously loaded module, or to instantiate a module for the first time
    if (not module['ref'] and not module['modulename']):
      debugLog(4, "registerModule called for module " + str(module['name']) + " without an existing reference or a module to instantiate.")
    elif (module['ref']):
      # If the reference is passed, it means this module has already been
      # instantiated and we should just refer to the existing instance

      # Check this module has not already been instantiated
      if (not self.modules.get(module['name'], None)):
        self.modules[module['name']] = {
          "ref": module['ref'],
          "type": module['type']
        }
        self.debugLog(4, "Registered module " + module['name'] + " by reference")
      else:
        self.debugLog(4, "Avoided re-registration of module " + module['name'] + ", which has already been loaded")

  def releaseBackgroundTasksLock(self):
    self.backgroundTasksLock.release()

  def resetChargeNowAmps(self):
    # Sets chargeNowAmps back to zero, so we follow the green energy
    # tracking again
    self.settings['chargeNowAmps'] = 0
    self.settings['chargeNowTimeEnd'] = 0

  def saveSettings(self):
    # Saves the volatile application settings (such as charger timings,
    # API credentials, etc) to a JSON file
    fileName = self.config['config']['settingsPath'] + '/settings.json'

    # Step 1 - Merge any config from other modules
    self.settings['carApiBearerToken'] = self.carapi.getCarApiBearerToken()
    self.settings['carApiRefreshToken'] = self.carapi.getCarApiRefreshToken()
    self.settings['carApiTokenExpireTime'] = self.carapi.getCarApiTokenExpireTime()

    # Step 2 - Write the settings dict to a JSON file
    with open(fileName, 'w') as outconfig:
      json.dump(self.settings, outconfig)

  def send_master_linkready1(self):

    if(self.config['config']['debugLevel'] >= 1):
        print(self.time_now() + ": Send master linkready1")

    # When master is powered on or reset, it sends 5 to 7 copies of this
    # linkready1 message followed by 5 copies of linkready2 (I've never seen
    # more or less than 5 of linkready2).
    #
    # This linkready1 message advertises master's TWCID to other slaves on the
    # network.
    # If a slave happens to have the same id as master, it will pick a new
    # random TWCID. Other than that, slaves don't seem to respond to linkready1.

    # linkready1 and linkready2 are identical except FC E1 is replaced by FB E2
    # in bytes 2-3. Both messages will cause a slave to pick a new id if the
    # slave's id conflicts with master.
    # If a slave stops sending heartbeats for awhile, master may send a series
    # of linkready1 and linkready2 messages in seemingly random order, which
    # means they don't indicate any sort of startup state.

    # linkready1 is not sent again after boot/reset unless a slave sends its
    # linkready message.
    # At that point, linkready1 message may start sending every 1-5 seconds, or
    # it may not be sent at all.
    # Behaviors I've seen:
    #   Not sent at all as long as slave keeps responding to heartbeat messages
    #   right from the start.
    #   If slave stops responding, then re-appears, linkready1 gets sent
    #   frequently.

    # One other possible purpose of linkready1 and/or linkready2 is to trigger
    # an error condition if two TWCs on the network transmit those messages.
    # That means two TWCs have rotary switches setting them to master mode and
    # they will both flash their red LED 4 times with top green light on if that
    # happens.

    # Also note that linkready1 starts with FC E1 which is similar to the FC D1
    # message that masters send out every 4 hours when idle. Oddly, the FC D1
    # message contains all zeros instead of the master's id, so it seems
    # pointless.

    # I also don't understand the purpose of having both linkready1 and
    # linkready2 since only two or more linkready2 will provoke a response from
    # a slave regardless of whether linkready1 was sent previously. Firmware
    # trace shows that slaves do something somewhat complex when they receive
    # linkready1 but I haven't been curious enough to try to understand what
    # they're doing. Tests show neither linkready1 or 2 are necessary. Slaves
    # send slave linkready every 10 seconds whether or not they got master
    # linkready1/2 and if a master sees slave linkready, it will start sending
    # the slave master heartbeat once per second and the two are then connected.
    self.sendMsg(bytearray(b'\xFC\xE1') + self.TWCID + self.masterSign + bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'))

  def send_master_linkready2(self):

    if(self.config['config']['debugLevel'] >= 1):
        print(self.time_now() + ": Send master linkready2")

    # This linkready2 message is also sent 5 times when master is booted/reset
    # and then not sent again if no other TWCs are heard from on the network.
    # If the master has ever seen a slave on the network, linkready2 is sent at
    # long intervals.
    # Slaves always ignore the first linkready2, but respond to the second
    # linkready2 around 0.2s later by sending five slave linkready messages.
    #
    # It may be that this linkready2 message that sends FB E2 and the master
    # heartbeat that sends fb e0 message are really the same, (same FB byte
    # which I think is message type) except the E0 version includes the TWC ID
    # of the slave the message is intended for whereas the E2 version has no
    # recipient TWC ID.
    #
    # Once a master starts sending heartbeat messages to a slave, it
    # no longer sends the global linkready2 message (or if it does,
    # they're quite rare so I haven't seen them).
    self.sendMsg(bytearray(b'\xFB\xE2') + self.TWCID + self.masterSign + bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'))

  def sendMsg(self, msg):
    # Send msg on the RS485 network. We'll escape bytes with a special meaning,
    # add a CRC byte to the message end, and add a C0 byte to the start and end
    # to mark where it begins and ends.

    msg = bytearray(msg)
    checksum = 0
    for i in range(1, len(msg)):
        checksum += msg[i]

    msg.append(checksum & 0xFF)

    # Escaping special chars:
    # The protocol uses C0 to mark the start and end of the message.  If a C0
    # must appear within the message, it is 'escaped' by replacing it with
    # DB and DC bytes.
    # A DB byte in the message is escaped by replacing it with DB DD.
    #
    # User FuzzyLogic found that this method of escaping and marking the start
    # and end of messages is based on the SLIP protocol discussed here:
    #   https://en.wikipedia.org/wiki/Serial_Line_Internet_Protocol
    i = 0
    while(i < len(msg)):
        if(msg[i] == 0xc0):
            msg[i:i+1] = b'\xdb\xdc'
            i = i + 1
        elif(msg[i] == 0xdb):
            msg[i:i+1] = b'\xdb\xdd'
            i = i + 1
        i = i + 1

    msg = bytearray(b'\xc0' + msg + b'\xc0')

    if(self.config['config']['debugLevel'] >= 9):
        print("Tx@" + self.time_now() + ": " + self.hex_str(msg))

    self.ser.write(msg)

    self.timeLastTx = time.time()

  def send_slave_linkready(self):
    # In the message below, \x1F\x40 (hex 0x1f40 or 8000 in base 10) refers to
    # this being a max 80.00Amp charger model.
    # EU chargers are 32A and send 0x0c80 (3200 in base 10).
    #
    # I accidentally changed \x1f\x40 to \x2e\x69 at one point, which makes the
    # master TWC immediately start blinking its red LED 6 times with top green
    # LED on. Manual says this means "The networked Wall Connectors have
    # different maximum current capabilities".
    msg = bytearray(b'\xFD\xE2') + self.TWCID + self.slaveSign + bytearray(b'\x1F\x40\x00\x00\x00\x00\x00\x00')
    if(self.protocolVersion == 2):
        msg += bytearray(b'\x00\x00')

    self.sendMsg(msg)

  def setChargeNowAmps(self, amps):
    # Accepts a number of amps to define the amperage at which we
    # should charge
    if (amps > self.config['config']['wiringMaxAmpsAllTWCs']):
      self.debugLog(1, "setChargeNowAmps failed because specified amps are above wiringMaxAmpsAllTWCs")
    elif (amps < 0):
      self.debugLog(1, "setChargeNowAmps failed as specified amps is less than 0")
    else:
      self.settings['chargeNowAmps'] = amps

  def setChargeNowTimeEnd(self, timeadd):
    self.settings['chargeNowTimeEnd'] = (time.time() + timeadd)

  def setChargingPerPolicy(self):
    # This function is called for the purpose of evaluating the charging
    # policy and matching the first rule which matches our scenario.

    # Once we have determined the maximum number of amps for all slaves to
    # share based on the policy, we call setMaxAmpsToDivideAmongSlaves to
    # distribute the designated power amongst slaves.

    # First, determine if it has been less than 30 seconds since the last
    # policy check. If so, skip for now
    if ((self.lastPolicyCheck + self.policyCheckInterval) > time.time()):
      return
    else:
      # Update last policy check time
      self.lastPolicyCheck = time.time()

    for policy in self.charge_policy:

      # Iterate through each set of match, condition and value sets
      iter = 0
      for match, condition, value in zip(policy['match'], policy['condition'], policy['value']):

        iter += 1
        self.debugLog(8, "Evaluating Policy match (" + str(match) + "), condition (" + condition + "), value (" + str(value) + "), iteration (" + str(iter) + ")")
        # Start by not having matched the condition
        is_matched = 0
        match = self.policyValue(match)
        value = self.policyValue(value)

        # Perform comparison
        if (condition == "gt"):
          # Match must be greater than value
          if (match > value):
            is_matched = 1
        if (condition == "lte"):
          # Match must be less or equal to value
          if (match <= value):
            is_matched = 1
        if (condition == "eq"):
          # Match must be equal to value
          if (match == value):
            is_matched = 1
        if (condition == "ne"):
          # Match must not be equal to value
          if (match != value):
            is_matched = 1
        if (condition == "false"):
          # Condition: false is a method to ensure a policy entry
          # is never matched, possibly for testing purposes
          is_matched = 0
        if (condition == "none"):
          # No condition exists.
          is_matched = 1

        # Check if we have met all criteria
        if (is_matched):

          # Have we checked all policy conditions yet?
          if (len(policy['match']) == iter):

            # Yes, we will now enforce policy
            self.debugLog(8, "All policy conditions have matched. Policy chosen is " + str(policy['name']))
            self.active_policy = str(policy['name'])

            # Determine which value to set the charging to
            if (policy['charge_amps'] == "value"):
              self.setMaxAmpsToDivideAmongSlaves(int(policy['value']))
              self.debugLog(10, 'Charge at %.2f' % int(policy['value']))
            else:
              self.setMaxAmpsToDivideAmongSlaves(self.policyValue(policy['charge_amps']))
              self.debugLog(10, 'Charge at %.2f' % self.policyValue(policy['charge_amps']))

            # If a background task is defined for this policy, queue it
            bgt = policy.get('background_task', None)
            if (bgt):
              self.queue_background_task({'cmd':bgt})

            # Now, finish processing
            return

          else:
            self.debugLog(8, "This policy condition has matched, but there are more to process.")

        else:
          self.debugLog(8, "Policy conditions were not matched.")
          break

  def setConsumption(self, source, value):
    # Accepts consumption values from one or more data sources
    # For now, this gives a sum value of all, but in future we could
    # average across sources perhaps, or do a primary/secondary priority
    self.consumptionValues[source] = value

  def setGeneration(self, source, value):
    self.generationValues[source] = value

  def sethassstatus(self, hass):
    # Stores the hassstatus object
    self.hassstatus = hass

  def setHomeLat(self, lat):
    self.settings['homeLat'] = lat

  def setHomeLon(self, lon):
    self.settings['homeLon'] = lon

  def setHourResumeTrackGreenEnergy(self, hour):
    self.settings['hourResumeTrackGreenEnergy'] = hour

  def setkWhDelivered(self, kWh):
    self.settings['kWhDelivered'] = kWh
    return True

  def setMasterTWCID(self, twcid):
    # This is called when TWCManager is in Slave mode, to track the
    # master's TWCID
    self.masterTWCID = twcid

  def setmqttstatus(self, mqtt):
    # Stores the mqttstatus object
    self.mqttstatus = mqtt

  def setMaxAmpsToDivideAmongSlaves(self, amps):

    # Use backgroundTasksLock to prevent changing maxAmpsToDivideAmongSlaves
    # if the main thread is in the middle of examining and later using
    # that value.
    self.getBackgroundTasksLock()

    if(amps > self.config['config']['wiringMaxAmpsAllTWCs']):
      # Never tell the slaves to draw more amps than the physical charger
      # wiring can handle.
      self.debugLog(1, "ERROR: specified maxAmpsToDivideAmongSlaves " + str(amps) +
       " > wiringMaxAmpsAllTWCs " + str(self.config['config']['wiringMaxAmpsAllTWCs']) +
       ".\nSee notes above wiringMaxAmpsAllTWCs in the 'Configuration parameters' section.")
      amps = self.config['config']['wiringMaxAmpsAllTWCs']

    self.maxAmpsToDivideAmongSlaves = amps

    self.releaseBackgroundTasksLock()

    # Now that we have updated the maxAmpsToDivideAmongSlaves, send update
    # to console / MQTT / etc
    self.queue_background_task({'cmd':'updateStatus'})

  def setNonScheduledAmpsMax(self, amps):
    self.settings['nonScheduledAmpsMax'] = amps

  def setScheduledAmpsDaysBitmap(self, bitmap):
    self.settings['scheduledAmpsDaysBitmap'] = bitmap

  def setScheduledAmpsMax(self, amps):
    self.settings['scheduledAmpsMax'] = amps

  def setScheduledAmpsStartHour(self, hour):
    self.settings['scheduledAmpsStartHour'] = hour

  def setScheduledAmpsEndHour(self, hour):
    self.settings['scheduledAmpsEndHour'] = hour

  def setSpikeAmps(self, amps):
    self.spikeAmpsToCancel6ALimit = amps

  def startCarsCharging(self):
    # This function is the opposite functionality to the stopCarsCharging function
    # below
    if (self.settings.get('chargeStopMode', "1") == "1"):
      self.queue_background_task({'cmd':'charge', 'charge':True})
    if (self.settings.get('chargeStopMode', "1") == "2"):
      self.settings['respondToSlaves'] = 1

  def stopCarsCharging(self):
    # This is called by components (mainly TWCSlave) who want to signal to us to
    # call our configured routine for stopping vehicles from charging.
    # The default setting is to use the Tesla API. Some people may not want to do
    # this, as it only works for Tesla vehicles and requires logging in with your
    # Tesla credentials. The alternate option is to stop responding to slaves

    # 1 = Stop the car(s) charging via the Tesla API
    # 2 = Stop the car(s) charging by refusing to respond to slave TWCs
    if (self.settings.get('chargeStopMode', "1") == "1"):
      self.queue_background_task({'cmd':'charge', 'charge':False})
    if (self.settings.get('chargeStopMode', "1") == "2"):
      self.settings['respondToSlaves'] = 0

  def time_now(self):
    return(datetime.now().strftime("%H:%M:%S" + (
        ".%f" if self.config['config']['displayMilliseconds'] else "")))

