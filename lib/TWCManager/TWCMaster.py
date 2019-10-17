#! /usr/bin/python3

from lib.TWCManager.TWCSlave import TWCSlave
from datetime import datetime
import queue
import serial
import threading
import time

class TWCMaster:

  backgroundTasksQueue = queue.Queue()
  backgroundTasksCmds = {}
  backgroundTasksLock = threading.Lock()
  carapi              = None
  chargeNowAmps       = 0
  chargeNowTimeEnd    = 0
  config              = None
  consumptionValues   = {}
  generationValues    = {}
  hassstatus          = None
  hourResumeTrackGreenEnergy = -1
  masterTWCID         = ''
  maxAmpsToDivideAmongSlaves = 0
  mqttstatus          = None
  nonScheduledAmpsMax = -1
  overrideMasterHeartbeatData = b''
  scheduledAmpsMax    = -1
  scheduledAmpsStartHour = -1
  scheduledAmpsEndHour = -1
  ser                 = None
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
    self.carapi = carapi
    self.config = config
    self.TWCID  = TWCID
    self.subtractChargerLoad = config['config']['subtractChargerLoad']

    # Connect to serial port
    self.ser = serial.Serial(config['config']['rs485adapter'], config['config']['baud'], timeout=0)

  def addSlaveTWC(self, slaveTWC):
    # Adds the Slave TWC to the Round Robin list
    return self.slaveTWCRoundRobin.append(slaveTWC)

  def checkChargeNowTime(self):
    # Returns the following values:
    # 0 = chargeNowTime has expired, reset chargeNow to 0
    # 1 = chargeNowAmps is set, charge at the specified value
    if (self.chargeNowTimeEnd > 0 and self.chargeNowTimeEnd < now):
      # We're beyond the one-day period where we want to charge at
      # chargeNowAmps, so reset the chargeNow variables.
      return 0
    elif (self.chargeNowTimeEnd > 0 and self.chargeNowAmps > 0):
      return 1

  def countSlaveTWC(self):
    return int(len(self.slaveTWCRoundRobin))

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
    return (self.chargeNowAmps)

  def getHourResumeTrackGreenEnergy(self):
    return self.hourResumeTrackGreenEnergy

  def getMasterTWCID(self):
    # This is called when TWCManager is in Slave mode, to track the
    # master's TWCID
    return self.masterTWCID

  def gethassstatus(self):
    return self.hassstatus

  def getMaxAmpsToDivideAmongSlaves(self):
    return self.maxAmpsToDivideAmongSlaves

  def getmqttstatus(self):
    return self.mqttstatus

  def getNonScheduledAmpsMax(self):
    return self.nonScheduledAmpsMax

  def getScheduledAmpsMax(self):
    return self.scheduledAmpsMax

  def getScheduledAmpsStartHour(self):
    return self.scheduledAmpsStartHour

  def getScheduledAmpsEndHour(self):
    return self.scheduledAmpsEndHour

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
    return maxAmpsToDivide

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

  def releaseBackgroundTasksLock(self):
    self.backgroundTasksLock.release()

  def resetChargeNowAmps(self):
    # Sets chargeNowAmps back to zero, so we follow the green energy
    # tracking again
    self.chargeNowAmps = 0
    self.chargeNowTimeEnd = 0

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

  def send_slave_linkready():
    # In the message below, \x1F\x40 (hex 0x1f40 or 8000 in base 10) refers to
    # this being a max 80.00Amp charger model.
    # EU chargers are 32A and send 0x0c80 (3200 in base 10).
    #
    # I accidentally changed \x1f\x40 to \x2e\x69 at one point, which makes the
    # master TWC immediately start blinking its red LED 6 times with top green
    # LED on. Manual says this means "The networked Wall Connectors have
    # different maximum current capabilities".
    msg = bytearray(b'\xFD\xE2') + self.TWCID + self.laveSign + bytearray(b'\x1F\x40\x00\x00\x00\x00\x00\x00')
    if(self.protocolVersion == 2):
        msg += bytearray(b'\x00\x00')

    send_msg(msg)

  def setChargeNowAmps(self, amps):
    # Accepts a number of amps to define the amperage at which we
    # should charge
    self.chargeNowAmps = amps

  def setChargeNowTimeEnd(self, time):
    self.chargeNowTimeEnd = (self.time.time() + time)

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

  def setHourResumeTrackGreenEnergy(self, hour):
    self.hourResumeTrackGreenEnergy = hour

  def setMasterTWCID(self, twcid):
    # This is called when TWCManager is in Slave mode, to track the
    # master's TWCID
    self.masterTWCID = twcid

  def setmqttstatus(self, mqtt):
    # Stores the mqttstatus object
    self.mqttstatus = mqtt

  def setMaxAmpsToChargeNowAmps(self):
    self.setMaxAmpsToDivideAmongSlaves(self.getChargeNowAmps())

  def setMaxAmpsToDivideAmongSlaves(self, amps):

    # Use backgroundTasksLock to prevent changing maxAmpsToDivideAmongSlaves
    # if the main thread is in the middle of examining and later using
    # that value.
    self.getBackgroundTasksLock()

    if(amps > self.config['config']['wiringMaxAmpsAllTWCs']):
      # Never tell the slaves to draw more amps than the physical charger
      # wiring can handle.
      debugLog(1, "ERROR: specified maxAmpsToDivideAmongSlaves " + str(amps) +
       " > wiringMaxAmpsAllTWCs " + str(self.config['config']['wiringMaxAmpsAllTWCs']) +
       ".\nSee notes above wiringMaxAmpsAllTWCs in the 'Configuration parameters' section.")
      amps = self.config['config']['wiringMaxAmpsAllTWCs']

    self.maxAmpsToDivideAmongSlaves = amps

    self.releaseBackgroundTasksLock()

  def setMaxAmpsToGreenEnergyTrack(self):
    # Set the Max Amps to divide among TWCs to the current Green Energy
    # generation value
    self.setMaxAmpsToDivideAmongSlaves(self.getMaxAmpsToDivideGreenEnergy())

  def setMaxAmpsToNonScheduledAmpsMax(self):
    self.setMaxAmpsToDivideAmongSlaves(self.getNonScheduledAmpsMax())

  def setMaxAmpsToScheduledAmpsMax(self):
    self.setMaxAmpsToDivideAmongSlaves(self.getScheduledAmpsMax())

  def setNonScheduledAmpsMax(self, amps):
    self.nonScheduledAmpsMax = amps

  def setScheduledAmpsMax(self, amps):
    self.scheduledAmpsMax = amps

  def setScheduledAmpsStartHour(self, hour):
    self.scheduledAmpsStartHour = hour

  def setScheduledAmpsEndHour(self, hour):
    self.scheduledAmpsEndHour = hour

  def setSpikeAmps(self, amps):
    self.spikeAmpsToCancel6ALimit = amps

  def time_now(self):
    return(datetime.now().strftime("%H:%M:%S" + (
        ".%f" if self.config['config']['displayMilliseconds'] else "")))

