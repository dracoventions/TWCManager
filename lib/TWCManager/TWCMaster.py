#! /usr/bin/python3

from lib.TWCManager.TWCSlave import TWCSlave
from datetime import datetime, timedelta
import json
import os.path
import queue
from sys import modules
from termcolor import colored
import threading
import time
from ww import f
import math


class TWCMaster:

    allowed_flex = 0
    backgroundTasksQueue = queue.Queue()
    backgroundTasksCmds = {}
    backgroundTasksLock = threading.Lock()
    config = None
    consumptionValues = {}
    debugLevel = 0
    generationValues = {}
    lastkWhMessage = time.time()
    lastkWhPoll = 0
    lastTWCResponseMsg = None
    masterTWCID = ""
    maxAmpsToDivideAmongSlaves = 0
    modules = {}
    nextHistorySnap = 0
    overrideMasterHeartbeatData = b""
    protocolVersion = 2
    releasedModules = []
    settings = {
        "chargeNowAmps": 0,
        "chargeStopMode": "1",
        "chargeNowTimeEnd": 0,
        "homeLat": 10000,
        "homeLon": 10000,
        "hourResumeTrackGreenEnergy": -1,
        "kWhDelivered": 119,
        "nonScheduledAmpsMax": 0,
        "respondToSlaves": 1,
        "scheduledAmpsDaysBitmap": 0x7F,
        "scheduledAmpsEndHour": -1,
        "scheduledAmpsMax": 0,
        "scheduledAmpsStartHour": -1,
    }
    slaveHeartbeatData = bytearray(
        [0x01, 0x0F, 0xA0, 0x0F, 0xA0, 0x00, 0x00, 0x00, 0x00]
    )
    slaveTWCs = {}
    slaveTWCRoundRobin = []
    stopTimeout = datetime.max
    spikeAmpsToCancel6ALimit = 16
    subtractChargerLoad = False
    teslaLoginAskLater = False
    TWCID = None

    # TWCs send a seemingly-random byte after their 2-byte TWC id in a number of
    # messages. I call this byte their "Sign" for lack of a better term. The byte
    # never changes unless the TWC is reset or power cycled. We use hard-coded
    # values for now because I don't know if there are any rules to what values can
    # be chosen. I picked 77 because it's easy to recognize when looking at logs.
    # These shouldn't need to be changed.
    masterSign = bytearray(b"\x77")
    slaveSign = bytearray(b"\x77")

    def __init__(self, TWCID, config):
        self.config = config
        self.debugLevel = config["config"]["debugLevel"]
        self.TWCID = TWCID
        self.subtractChargerLoad = config["config"]["subtractChargerLoad"]
        self.advanceHistorySnap()

        # Register ourself as a module, allows lookups via the Module architecture
        self.registerModule({"name": "master", "ref": self, "type": "Master"})

    def addkWhDelivered(self, kWh):
        self.settings["kWhDelivered"] = self.settings.get("kWhDelivered", 0) + kWh

    def addSlaveTWC(self, slaveTWC):
        # Adds the Slave TWC to the Round Robin list
        return self.slaveTWCRoundRobin.append(slaveTWC)

    def advanceHistorySnap(self):
        try:
          futureSnap = datetime.now().astimezone() + timedelta(minutes=5)
          self.nextHistorySnap = futureSnap.replace(
              minute=math.floor(futureSnap.minute / 5) * 5, second=0, microsecond=0
          )
        except ValueError as e:
          self.debugLog(10, "TWCMaster", "Exception in advanceHistorySnap: " + str(e))

    def checkScheduledCharging(self):

        # Check if we're within the hours we must use scheduledAmpsMax instead
        # of nonScheduledAmpsMax
        blnUseScheduledAmps = 0
        ltNow = time.localtime()

        if (
            self.getScheduledAmpsMax() > 0
            and self.settings.get("scheduledAmpsStartHour", -1) > -1
            and self.getScheduledAmpsEndHour() > -1
            and self.getScheduledAmpsDaysBitmap() > 0
        ):
            if (
                self.settings.get("scheduledAmpsStartHour", -1)
                > self.getScheduledAmpsEndHour()
            ):
                # We have a time like 8am to 7am which we must interpret as the
                # 23-hour period after 8am or before 7am. Since this case always
                # crosses midnight, we only ensure that scheduledAmpsDaysBitmap
                # is set for the day the period starts on. For example, if
                # scheduledAmpsDaysBitmap says only schedule on Monday, 8am to
                # 7am, we apply scheduledAmpsMax from Monday at 8am to Monday at
                # 11:59pm, and on Tuesday at 12am to Tuesday at 6:59am.
                hourNow = ltNow.tm_hour + (ltNow.tm_min / 60)
                if (
                    hourNow >= self.settings.get("scheduledAmpsStartHour", -1)
                    and (self.getScheduledAmpsDaysBitmap() & (1 << ltNow.tm_wday))
                ) or (
                    hourNow < self.getScheduledAmpsEndHour()
                    and (self.getScheduledAmpsDaysBitmap() & (1 << yesterday))
                ):
                    blnUseScheduledAmps = 1
            else:
                # We have a time like 7am to 8am which we must interpret as the
                # 1-hour period between 7am and 8am.
                hourNow = ltNow.tm_hour + (ltNow.tm_min / 60)
                if (
                    hourNow >= self.settings.get("scheduledAmpsStartHour", -1)
                    and hourNow < self.getScheduledAmpsEndHour()
                    and (self.getScheduledAmpsDaysBitmap() & (1 << ltNow.tm_wday))
                ):
                    blnUseScheduledAmps = 1
        return blnUseScheduledAmps

    def convertAmpsToWatts(self, amps):
        (voltage, phases) = self.getVoltageMeasurement()
        return phases * voltage * amps

    def convertWattsToAmps(self, watts):
        (voltage, phases) = self.getVoltageMeasurement()
        return watts / (phases * voltage)

    def countSlaveTWC(self):
        return int(len(self.slaveTWCRoundRobin))

    def debugLog(self, minlevel, function, message):
        # Trim/pad the module name as needed
        if len(function) < 10:
            for a in range(len(function), 10):
                function += " "

        if self.debugLevel >= minlevel:
            print(
                colored(self.time_now() + " ", "yellow")
                + colored(f("{function}"), "green")
                + colored(f(" {minlevel} "), "cyan")
                + f("{message}")
            )

    def deleteBackgroundTask(self, task):
        del self.backgroundTasksCmds[task["cmd"]]

    def doneBackgroundTask(self):
        # task_done() must be called to let the queue know the task is finished.
        # backgroundTasksQueue.join() can then be used to block until all tasks
        # in the queue are done.
        self.backgroundTasksQueue.task_done()

    def getAllowedFlex(self):
        return self.allowedFlex

    def getBackgroundTask(self):
        return self.backgroundTasksQueue.get()

    def getBackgroundTasksLock(self):
        self.backgroundTasksLock.acquire()

    def getChargeNowAmps(self):
        # Returns the currently configured Charge Now Amps setting
        chargenow = int(self.settings.get("chargeNowAmps", 0))
        if chargenow > 0:
            return chargenow
        else:
            return 0

    def getHourResumeTrackGreenEnergy(self):
        return self.settings.get("hourResumeTrackGreenEnergy", -1)

    def getMasterTWCID(self):
        # This is called when TWCManager is in Slave mode, to track the
        # master's TWCID
        return self.masterTWCID

    def getkWhDelivered(self):
        return self.settings["kWhDelivered"]

    def getMaxAmpsToDivideAmongSlaves(self):
        if self.maxAmpsToDivideAmongSlaves > 0:
            return self.maxAmpsToDivideAmongSlaves
        else:
            return 0

    def getModuleByName(self, name):
        module = self.modules.get(name, None)
        if module:
            return module["ref"]
        else:
            return None

    def getModulesByType(self, type):
        matched = []
        for module in self.modules:
            modinfo = self.modules[module]
            if modinfo["type"] == type:
                matched.append({"name": module, "ref": modinfo["ref"]})
        return matched

    def getScheduledAmpsDaysBitmap(self):
        return self.settings.get("scheduledAmpsDaysBitmap", 0x7F)

    def getNonScheduledAmpsMax(self):
        nschedamps = int(self.settings.get("nonScheduledAmpsMax", 0))
        if nschedamps > 0:
            return nschedamps
        else:
            return 0

    def getScheduledAmpsMax(self):
        schedamps = int(self.settings.get("scheduledAmpsMax", 0))
        if schedamps > 0:
            return schedamps
        else:
            return 0

    def getScheduledAmpsStartHour(self):
        return self.settings.get("scheduledAmpsStartHour", -1)

    def getScheduledAmpsEndHour(self):
        return self.settings.get("scheduledAmpsEndHour", -1)

    def getSlaveLifetimekWh(self):

        # This function is called from a Scheduled Task
        # If it's been at least 1 minute, then query all known Slave TWCs
        # to determine their lifetime kWh and per-phase voltages
        now = time.time()
        if now >= self.lastkWhPoll + 60:
            for slaveTWC in self.getSlaveTWCs():
                self.getModuleByName("RS485").send(
                    bytearray(b"\xFB\xEB")
                    + self.TWCID
                    + slaveTWC.TWCID
                    + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00")
                )
            self.lastkWhPoll = now

    def getSlaveSign(self):
        return self.slaveSign

    def getSpikeAmps(self):
        return self.spikeAmpsToCancel6ALimit

    def getTimeLastTx(self):
        return self.getModuleByName("RS485").timeLastTx

    def getVehicleVIN(self, slaveID, part):
        prefixByte = None
        if int(part) == 0:
            prefixByte = bytearray(b"\xFB\xEE")
        if int(part) == 1:
            prefixByte = bytearray(b"\xFB\xEF")
        if int(part) == 2:
            prefixByte = bytearray(b"\xFB\xF1")

        if prefixByte:
            self.getModuleByName("RS485").send(
                prefixByte
                + self.TWCID
                + slaveID
                + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00")
            )

    def deleteSlaveTWC(self, deleteSlaveID):
        for i in range(0, len(self.slaveTWCRoundRobin)):
            if self.slaveTWCRoundRobin[i].TWCID == deleteSlaveID:
                del self.slaveTWCRoundRobin[i]
                break
        try:
            del self.slaveTWCs[deleteSlaveID]
        except KeyError:
            pass

    def getChargerLoad(self):
        # Calculate in watts the load that the charger is generating so
        # that we can exclude it from the consumption if necessary
        return self.convertAmpsToWatts(self.getTotalAmpsInUse())

    def getConsumption(self):
        consumptionVal = 0

        for key in self.consumptionValues:
            consumptionVal += float(self.consumptionValues[key])

        if consumptionVal < 0:
            consumptionVal = 0

        return float(consumptionVal)

    def getFakeTWCID(self):
        return self.TWCID

    def getGeneration(self):
        generationVal = 0

        # Currently, our only logic is to add all of the values together
        for key in self.generationValues:
            generationVal += float(self.generationValues[key])

        if generationVal < 0:
            generationVal = 0

        return float(generationVal)

    def getGenerationOffset(self):
        # Returns the number of watts to subtract from the solar generation stats
        # This is consumption + charger load if subtractChargerLoad is enabled
        # Or simply consumption if subtractChargerLoad is disabled
        generationOffset = self.getConsumption()
        if self.subtractChargerLoad:
            generationOffset -= self.getChargerLoad()
        if generationOffset < 0:
            generationOffset = 0
        return float(generationOffset)

    def getHomeLatLon(self):
        # Returns Lat/Lon coordinates to check if car location is
        # at home
        latlon = [10000, 10000]
        latlon[0] = self.settings.get("homeLat", 10000)
        latlon[1] = self.settings.get("homeLon", 10000)
        return latlon

    def getMasterHeartbeatOverride(self):
        return self.overrideMasterHeartbeatData

    def getMaxAmpsToDivideGreenEnergy(self):
        # Calculate our current generation and consumption in watts
        generationW = float(self.getGeneration())
        consumptionW = float(self.getConsumption())

        # Calculate what we should offer to align with green energy
        #
        # The current offered shouldn't increase more than / must
        # decrease at least the current gap between generation and
        # consumption.

        currentOffer = max(
            self.getMaxAmpsToDivideAmongSlaves(),
            self.num_cars_charging_now() * self.config["config"]["minAmpsPerTWC"],
        )
        newOffer = currentOffer + self.convertWattsToAmps(generationW - consumptionW)

        # This is the *de novo* calculation of how much we can offer
        #
        # Fetches and uses consumptionW separately
        generationOffset = self.getGenerationOffset()
        solarW = float(generationW - generationOffset)

        # Offer the smaller of the two, but not less than zero.
        return max(min(newOffer, self.convertWattsToAmps(solarW)), 0)

    def getNormalChargeLimit(self, ID):
        if "chargeLimits" in self.settings and str(ID) in self.settings["chargeLimits"]:
            result = self.settings["chargeLimits"][str(ID)]
            if type(result) is int:
                result = (result, 0)
            return (True, result[0], result[1])
        return (False, None, None)

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
            for module in self.getModulesByType("Status"):
                module["ref"].setStatus(
                    slaveTWC.TWCID,
                    "amps_in_use",
                    "ampsInUse",
                    slaveTWC.reportedAmpsActual,
                    "A",
                )

        for module in self.getModulesByType("Status"):
            module["ref"].setStatus(
                bytes("all", "UTF-8"), "total_amps_in_use", "totalAmpsInUse", totalAmps, "A"
            )

        self.debugLog(
            10, "TWCMaster", "Total amps all slaves are using: " + str(totalAmps)
        )
        return totalAmps

    def getVoltageMeasurement(self):
        slavesWithVoltage = [
            slave for slave in self.getSlaveTWCs() if slave.voltsPhaseA > 0
        ]
        if len(slavesWithVoltage) == 0:
            # No slaves support returning voltage
            return (
                self.config["config"].get("defaultVoltage", 240),
                self.config["config"].get("numberOfPhases", 1),
            )

        total = 0
        phases = 0
        if any([slave.voltsPhaseC > 0 for slave in slavesWithVoltage]):
            # Three-phase system
            phases = 3
            if all([slave.voltsPhaseC > 0 for slave in slavesWithVoltage]):
                total = sum(
                    [
                        (slave.voltsPhaseA + slave.voltsPhaseB + slave.voltsPhaseC)
                        for slave in slavesWithVoltage
                    ]
                )
            else:
                self.debugLog(
                    1,
                    "TWCMaster",
                    "FATAL:  Mix of three-phase and single-phase not currently supported.",
                )
                return (
                    self.config["config"].get("defaultVoltage", 240),
                    self.config["config"].get("numberOfPhases", 1),
                )
        else:
            # Single-phase system
            total = sum([slave.voltsPhaseA for slave in slavesWithVoltage])
            phases = 1

        return (total / (phases * len(slavesWithVoltage)), phases)

    def hex_str(self, s: str):
        return " ".join("{:02X}".format(ord(c)) for c in s)

    def hex_str(self, ba: bytearray):
        return " ".join("{:02X}".format(c) for c in ba)

    def loadSettings(self):
        # Loads the volatile application settings (such as charger timings,
        # API credentials, etc) from a JSON file

        # Step 1 - Load settings from JSON file
        if not os.path.exists(self.config["config"]["settingsPath"] + "/settings.json"):
            self.settings = {}
            return

        with open(
            self.config["config"]["settingsPath"] + "/settings.json", "r"
        ) as inconfig:
            try:
                self.settings = json.load(inconfig)
            except Exception as e:
                self.debugLog(
                    1,
                    "TWCMaster",
                    "There was an exception whilst loading settings file "
                    + self.config["config"]["settingsPath"]
                    + "/settings.json",
                )
                self.debugLog(
                    1,
                    "TWCMaster",
                    "Some data may have been loaded. This may be because the file is being created for the first time.",
                )
                self.debugLog(
                    1,
                    "TWCMaster",
                    "It may also be because you are upgrading from a TWCManager version prior to v1.1.4, which used the old settings file format.",
                )
                self.debugLog(
                    1,
                    "TWCMaster",
                    "If this is the case, you may need to locate the old config file and migrate some settings manually.",
                )
                self.debugLog(11, "TWCMaster", str(e))

        # Step 2 - Send settings to other modules
        carapi = self.getModuleByName("TeslaAPI")
        carapi.setCarApiBearerToken(self.settings.get("carApiBearerToken", ""))
        carapi.setCarApiRefreshToken(self.settings.get("carApiRefreshToken", ""))
        carapi.setCarApiTokenExpireTime(self.settings.get("carApiTokenExpireTime", ""))

    def master_id_conflict():
        # We're playing fake slave, and we got a message from a master with our TWCID.
        # By convention, as a slave we must change our TWCID because a master will not.
        self.TWCID[0] = random.randint(0, 0xFF)
        self.TWCID[1] = random.randint(0, 0xFF)

        # Real slaves change their sign during a conflict, so we do too.
        self.slaveSign[0] = random.randint(0, 0xFF)

        print(
            time_now() + ": Master's TWCID matches our fake slave's TWCID.  "
            "Picked new random TWCID %02X%02X with sign %02X"
            % (self.TWCID[0], self.TWCID[1], self.slaveSign[0])
        )

    def newSlave(self, newSlaveID, maxAmps):
        try:
            slaveTWC = self.slaveTWCs[newSlaveID]
            # We didn't get KeyError exception, so this slave is already in
            # slaveTWCs and we can simply return it.
            return slaveTWC
        except KeyError:
            pass

        slaveTWC = TWCSlave(newSlaveID, maxAmps, self.config, self)
        self.slaveTWCs[newSlaveID] = slaveTWC
        self.addSlaveTWC(slaveTWC)

        if self.countSlaveTWC() > 3:
            print(
                "WARNING: More than 3 slave TWCs seen on network.  "
                "Dropping oldest: " + self.hex_str(self.getSlaveTWCID(0)) + "."
            )
            self.deleteSlaveTWC(self.getSlaveTWCID(0))

        return slaveTWC

    def num_cars_charging_now(self):

        carsCharging = 0
        for slaveTWC in self.getSlaveTWCs():
            if slaveTWC.reportedAmpsActual >= 1.0:
                if slaveTWC.isCharging == 0:
                    # We have detected that a vehicle has started charging on this Slave TWC
                    # Attempt to request the vehicle's VIN
                    slaveTWC.isCharging = 1
                    self.queue_background_task({"cmd": "getVehicleVIN", "slaveTWC": slaveTWC.TWCID, "vinPart": 0})

                    # Record our VIN query timestamp
                    slaveTWC.lastVINQuery = time.time()
                    slaveTWC.vinQueryAttempt = 1

                    # Record start of current charging session
                    self.recordVehicleSessionStart(slaveTWC)
            else:
                if slaveTWC.isCharging == 1:
                    # A vehicle was previously charging and is no longer charging
                    # Clear the VIN details for this slave and move the last
                    # vehicle's VIN to lastVIN
                    slaveTWC.VINData = ["", "", ""]
                    if slaveTWC.currentVIN:
                        slaveTWC.lastVIN = slaveTWC.currentVIN
                    slaveTWC.currentVIN = ""
                    self.updateVINStatus()

                    # Stop querying for Vehicle VIN
                    slaveTWC.lastVINQuery = 0
                    slaveTWC.vinQueryAttempt = 0

                    # Close off the current charging session
                    self.recordVehicleSessionEnd(slaveTWC)
                slaveTWC.isCharging = 0
            carsCharging += slaveTWC.isCharging
            for module in self.getModulesByType("Status"):
                module["ref"].setStatus(
                    slaveTWC.TWCID, "cars_charging", "carsCharging", slaveTWC.isCharging, ""
                )
        self.debugLog(
            10, "TWCMaster", "Number of cars charging now: " + str(carsCharging)
        )

        if carsCharging == 0:
            self.stopTimeout = datetime.max

        return carsCharging

    def queue_background_task(self, task):

        if task["cmd"] in self.backgroundTasksCmds:
            # Some tasks, like cmd='charge', will be called once per second until
            # a charge starts or we determine the car is done charging.  To avoid
            # wasting memory queing up a bunch of these tasks when we're handling
            # a charge cmd already, don't queue two of the same task.
            return

        # Insert task['cmd'] in backgroundTasksCmds to prevent queuing another
        # task['cmd'] till we've finished handling this one.
        self.backgroundTasksCmds[task["cmd"]] = True

        # Queue the task to be handled by background_tasks_thread.
        self.backgroundTasksQueue.put(task)

    def registerModule(self, module):
        # This function is used during module instantiation to either reference a
        # previously loaded module, or to instantiate a module for the first time
        if not module["ref"] and not module["modulename"]:
            debugLog(
                2,
                f(
                    "registerModule called for module {colored(module['name'], 'red')} without an existing reference or a module to instantiate."
                ),
            )
        elif module["ref"]:
            # If the reference is passed, it means this module has already been
            # instantiated and we should just refer to the existing instance

            # Check this module has not already been instantiated
            if not self.modules.get(module["name"], None):
                if not module["name"] in self.releasedModules:
                    self.debugLog(
                        7,
                        "TWCMaster",
                        f("Registered module {colored(module['name'], 'red')}"),
                    )
                    self.modules[module["name"]] = {
                        "ref": module["ref"],
                        "type": module["type"],
                    }
            else:
                self.debugLog(
                    7,
                    "TWCMaster",
                    f(
                        "Avoided re-registration of module {colored(module['name'], 'red')}, which has already been loaded"
                    ),
                )

    def recordVehicleSessionEnd(self, slaveTWC):
        # This function is called when a vehicle charge session ends.
        # If we have a last vehicle VIN set, close off the charging session
        # for this vehicle and save the settings.
        if (not self.settings.get("Vehicles", None)):
          self.settings["Vehicles"] = {}
        if (self.settings["Vehicles"].get(slaveTWC.lastVIN, None)):
          if (self.settings["Vehicles"][slaveTWC.lastVIN].get("startkWh", 0) > 0):
            # End current session
            delta = (slaveTWC.lifetimekWh - self.settings["Vehicles"][slaveTWC.lastVIN]["startkWh"])
            self.settings["Vehicles"][slaveTWC.lastVIN]["startkWh"] = 0
            self.settings["Vehicles"][slaveTWC.lastVIN]["totalkWh"] += delta
            self.saveSettings()

        # Update Charge Session details in logging modules
        for module in self.getModulesByType("Logging"):
            module["ref"].stopChargeSession({
                "TWCID": slaveTWC.TWCID,
                "endkWh": slaveTWC.lifetimekWh,
                "endTime": int(time.time()),
                "endFormat": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })


    def recordVehicleSessionStart(self, slaveTWC):
        # Update Charge Session details in logging modules
        for module in self.getModulesByType("Logging"):
            module["ref"].startChargeSession({
                "TWCID": slaveTWC.TWCID,
                "startkWh": slaveTWC.lifetimekWh,
                "startTime": int(time.time()),
                "startFormat": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    def recordVehicleVIN(self, slaveTWC):
        # Record Slave TWC ID as being capable of reporting VINs, if it is not
        # already.
        twcid = "%02X%02X" % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
        if (not self.settings.get("SlaveTWCs", None)):
            self.settings["SlaveTWCs"] = {}
        if (not self.settings["SlaveTWCs"].get(twcid, None)):
            self.settings["SlaveTWCs"][twcid] = {}
        if (not self.settings["SlaveTWCs"][twcid].get("supportsVINQuery", 0)):
            self.settings["SlaveTWCs"][twcid]["supportsVINQuery"] = 1
            self.saveSettings()

        # Increment sessions counter for this VIN in persistent settings file
        if (not self.settings.get("Vehicles", None)):
          self.settings["Vehicles"] = {}
        if (not self.settings["Vehicles"].get(slaveTWC.currentVIN, None)):
          self.settings["Vehicles"][slaveTWC.currentVIN] = {
            "chargeSessions": 1,
            "startkWh": slaveTWC.lifetimekWh,
            "totalkWh": 0
          }
        else:
          self.settings["Vehicles"][slaveTWC.currentVIN]["chargeSessions"] += 1
          self.settings["Vehicles"][slaveTWC.currentVIN]["startkWh"] = slaveTWC.lifetimekWh
          if (not self.settings["Vehicles"][slaveTWC.currentVIN].get("totalkWh", None)):
            self.settings["Vehicles"][slaveTWC.currentVIN]["totalkWh"] = 0
        self.saveSettings()

        # Update Charge Session details in logging modules
        for module in self.getModulesByType("Logging"):
            module["ref"].updateChargeSession({
                "TWCID": slaveTWC.TWCID,
                "vehicleVIN": slaveTWC.currentVIN
            })

    def releaseBackgroundTasksLock(self):
        self.backgroundTasksLock.release()

    def releaseModule(self, path, module):
        # Removes a module from the modules dict
        # This ensures we do not continue to call the module if it is
        # inoperable
        self.releasedModules.append(module)
        if self.modules.get(module, None):
            del self.modules[module]

        fullname = path + "." + module
        if modules.get(fullname, None):
            del modules[fullname]

        self.debugLog(7, "TWCMaster", f("Released module {colored(module, 'red')}"))

    def removeNormalChargeLimit(self, ID):
        if "chargeLimits" in self.settings and str(ID) in self.settings["chargeLimits"]:
            del self.settings["chargeLimits"][str(ID)]
            self.saveSettings()

    def resetChargeNowAmps(self):
        # Sets chargeNowAmps back to zero, so we follow the green energy
        # tracking again
        self.settings["chargeNowAmps"] = 0
        self.settings["chargeNowTimeEnd"] = 0

    def retryVINQuery(self):
        # For each Slave TWC, check if it's been more than 60 seconds since the last
        # VIN query without a VIN. If so, query again.
        for slaveTWC in self.getSlaveTWCs():
           if slaveTWC.isCharging == 1:
              if (slaveTWC.lastVINQuery > 0 and slaveTWC.vinQueryAttempt < 6 and not slaveTWC.currentVIN):
                 if ((time.time() - slaveTWC.lastVINQuery) >= 60):
                     self.queue_background_task({"cmd": "getVehicleVIN", "slaveTWC": slaveTWC.TWCID, "vinPart": 0})
                     slaveTWC.vinQueryAttempt += 1
                     slaveTWC.lastVINQuery = time.time()
           else:
              slaveTWC.lastVINQuery = 0

    def saveNormalChargeLimit(self, ID, outsideLimit, lastApplied):
        if not "chargeLimits" in self.settings:
            self.settings["chargeLimits"] = dict()

        self.settings["chargeLimits"][str(ID)] = (outsideLimit, lastApplied)
        self.saveSettings()

    def saveSettings(self):
        # Saves the volatile application settings (such as charger timings,
        # API credentials, etc) to a JSON file
        fileName = self.config["config"]["settingsPath"] + "/settings.json"

        # Step 1 - Merge any config from other modules
        carapi = self.getModuleByName("TeslaAPI")
        self.settings["carApiBearerToken"] = carapi.getCarApiBearerToken()
        self.settings["carApiRefreshToken"] = carapi.getCarApiRefreshToken()
        self.settings["carApiTokenExpireTime"] = carapi.getCarApiTokenExpireTime()

        # Step 2 - Write the settings dict to a JSON file
        with open(fileName, "w") as outconfig:
            try:
                json.dump(self.settings, outconfig)
            except TypeError as e:
                self.debugLog(1, "TWCMaster", "Exception raised while attempting to save settings file:")
                self.debugLog(1, "TWCMaster", str(e))

    def send_master_linkready1(self):

        self.debugLog(8, "TWCMaster", "Send master linkready1")

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
        self.getModuleByName("RS485").send(
            bytearray(b"\xFC\xE1")
            + self.TWCID
            + self.masterSign
            + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00")
        )

    def send_master_linkready2(self):

        self.debugLog(8, "TWCMaster", "Send master linkready2")

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
        self.getModuleByName("RS485").send(
            bytearray(b"\xFB\xE2")
            + self.TWCID
            + self.masterSign
            + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00")
        )

    def send_slave_linkready(self):
        # In the message below, \x1F\x40 (hex 0x1f40 or 8000 in base 10) refers to
        # this being a max 80.00Amp charger model.
        # EU chargers are 32A and send 0x0c80 (3200 in base 10).
        #
        # I accidentally changed \x1f\x40 to \x2e\x69 at one point, which makes the
        # master TWC immediately start blinking its red LED 6 times with top green
        # LED on. Manual says this means "The networked Wall Connectors have
        # different maximum current capabilities".
        msg = (
            bytearray(b"\xFD\xE2")
            + self.TWCID
            + self.slaveSign
            + bytearray(b"\x1F\x40\x00\x00\x00\x00\x00\x00")
        )
        if self.protocolVersion == 2:
            msg += bytearray(b"\x00\x00")

        self.getModuleByName("RS485").send(msg)

    def sendStartCommand(self):
        # This function will loop through each of the Slave TWCs, and send them the start command.
        for slaveTWC in self.getSlaveTWCs():
            self.getModuleByName("RS485").send(
                bytearray(b"\xFC\xB1")
                + self.TWCID
                + slaveTWC.TWCID
                + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            )

    def sendStopCommand(self):
        # This function will loop through each of the Slave TWCs, and send them the stop command.
        for slaveTWC in self.getSlaveTWCs():
            self.getModuleByName("RS485").send(
                bytearray(b"\xFC\xB2")
                + self.TWCID
                + slaveTWC.TWCID
                + bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00")
            )

    def setAllowedFlex(self, amps):
        self.allowedFlex = amps if amps >= 0 else 0

    def setChargeNowAmps(self, amps):
        # Accepts a number of amps to define the amperage at which we
        # should charge
        if amps > self.config["config"]["wiringMaxAmpsAllTWCs"]:
            self.debugLog(
                1,
                "TWCMaster",
                "setChargeNowAmps failed because specified amps are above wiringMaxAmpsAllTWCs",
            )
        elif amps < 0:
            self.debugLog(
                1,
                "TWCMaster",
                "setChargeNowAmps failed as specified amps is less than 0",
            )
        else:
            self.settings["chargeNowAmps"] = amps

    def setChargeNowTimeEnd(self, timeadd):
        self.settings["chargeNowTimeEnd"] = time.time() + timeadd

    def setConsumption(self, source, value):
        # Accepts consumption values from one or more data sources
        # For now, this gives a sum value of all, but in future we could
        # average across sources perhaps, or do a primary/secondary priority
        self.consumptionValues[source] = value

    def setGeneration(self, source, value):
        self.generationValues[source] = value

    def setHomeLat(self, lat):
        self.settings["homeLat"] = lat

    def setHomeLon(self, lon):
        self.settings["homeLon"] = lon

    def setHourResumeTrackGreenEnergy(self, hour):
        self.settings["hourResumeTrackGreenEnergy"] = hour

    def setkWhDelivered(self, kWh):
        self.settings["kWhDelivered"] = kWh
        return True

    def setMasterTWCID(self, twcid):
        # This is called when TWCManager is in Slave mode, to track the
        # master's TWCID
        self.masterTWCID = twcid

    def setMaxAmpsToDivideAmongSlaves(self, amps):

        # Use backgroundTasksLock to prevent changing maxAmpsToDivideAmongSlaves
        # if the main thread is in the middle of examining and later using
        # that value.
        self.getBackgroundTasksLock()

        if amps > self.config["config"]["wiringMaxAmpsAllTWCs"]:
            # Never tell the slaves to draw more amps than the physical charger
            # wiring can handle.
            self.debugLog(
                1,
                "TWCMaster",
                "ERROR: specified maxAmpsToDivideAmongSlaves "
                + str(amps)
                + " > wiringMaxAmpsAllTWCs "
                + str(self.config["config"]["wiringMaxAmpsAllTWCs"])
                + ".\nSee notes above wiringMaxAmpsAllTWCs in the 'Configuration parameters' section.",
            )
            amps = self.config["config"]["wiringMaxAmpsAllTWCs"]

        self.maxAmpsToDivideAmongSlaves = amps

        self.releaseBackgroundTasksLock()

        # Now that we have updated the maxAmpsToDivideAmongSlaves, send update
        # to console / MQTT / etc
        self.queue_background_task({"cmd": "updateStatus"})

    def setNonScheduledAmpsMax(self, amps):
        self.settings["nonScheduledAmpsMax"] = amps

    def setScheduledAmpsDaysBitmap(self, bitmap):
        self.settings["scheduledAmpsDaysBitmap"] = bitmap

    def setScheduledAmpsMax(self, amps):
        self.settings["scheduledAmpsMax"] = amps

    def setScheduledAmpsStartHour(self, hour):
        self.settings["scheduledAmpsStartHour"] = hour

    def setScheduledAmpsEndHour(self, hour):
        self.settings["scheduledAmpsEndHour"] = hour

    def setSpikeAmps(self, amps):
        self.spikeAmpsToCancel6ALimit = amps

    def snapHistoryData(self):
        snaptime = self.nextHistorySnap
        now = datetime.now().astimezone()
        avgCurrent = 0

        if now < snaptime:
            return

        for slave in self.getSlaveTWCs():
            avgCurrent += slave.historyAvgAmps
            slave.historyNumSamples = 0
        self.advanceHistorySnap()

        if avgCurrent > 0:
            periodTimestamp = snaptime - timedelta(minutes=5)

            if not "history" in self.settings:
                self.settings["history"] = []

            self.settings["history"].append(
                (
                    periodTimestamp.isoformat(timespec="seconds"),
                    self.convertAmpsToWatts(avgCurrent),
                )
            )

            self.settings["history"] = [
                e
                for e in self.settings["history"]
                if datetime.fromisoformat(e[0]) >= (now - timedelta(days=2))
            ]
            self.saveSettings()

    def startCarsCharging(self):
        # This function is the opposite functionality to the stopCarsCharging function
        # below
        if self.settings.get("chargeStopMode", "1") == "1":
            self.queue_background_task({"cmd": "charge", "charge": True})
            self.getModuleByName("Policy").clearOverride()
        if self.settings.get("chargeStopMode", "1") == "2":
            self.settings["respondToSlaves"] = 1
        if self.settings.get("chargeStopMode", "1") == "3":
            self.queue_background_task({"cmd": "charge", "charge": True})

    def stopCarsCharging(self):
        # This is called by components (mainly TWCSlave) who want to signal to us to
        # call our configured routine for stopping vehicles from charging.
        # The default setting is to use the Tesla API. Some people may not want to do
        # this, as it only works for Tesla vehicles and requires logging in with your
        # Tesla credentials. The alternate option is to stop responding to slaves

        # 1 = Stop the car(s) charging via the Tesla API
        # 2 = Stop the car(s) charging by refusing to respond to slave TWCs
        # 3 = Send TWC Stop command to each slave
        if self.settings.get("chargeStopMode", "1") == "1":
            self.queue_background_task({"cmd": "charge", "charge": False})
            if self.stopTimeout == datetime.max:
                self.stopTimeout = datetime.now() + timedelta(seconds = 10)
            elif datetime.now() > self.stopTimeout:
                self.getModuleByName("Policy").overrideLimit()
        if self.settings.get("chargeStopMode", "1") == "2":
            self.settings["respondToSlaves"] = 0
        if self.settings.get("chargeStopMode", "1") == "3":
            self.sendStopCommand()

    def time_now(self):
        return datetime.now().strftime(
            "%H:%M:%S" + (".%f" if self.config["config"]["displayMilliseconds"] else "")
        )

    def updateSlaveLifetime(self, sender, kWh, vPA, vPB, vPC):
        for slaveTWC in self.getSlaveTWCs():
            if slaveTWC.TWCID == sender:
                slaveTWC.setLifetimekWh(kWh)
                slaveTWC.setVoltage(vPA, vPB, vPC)

                # Publish Lifetime kWh Value via Status modules
                for module in self.getModulesByType("Status"):
                    module["ref"].setStatus(
                        slaveTWC.TWCID,
                        "lifetime_kwh",
                        "lifetimekWh",
                        slaveTWC.lifetimekWh,
                        "kWh",
                    )

                    # Publish phase 1, 2 and 3 values via Status modules
                    for phase in ("A", "B", "C"):
                        for module in self.getModulesByType("Status"):
                            module["ref"].setStatus(
                                slaveTWC.TWCID,
                                "voltage_phase_" + phase.lower(),
                                "voltagePhase" + phase,
                                getattr(slaveTWC, "voltsPhase" + phase, 0),
                                "V",
                            )

    def updateVINStatus(self):
        # update current and last VIN IDs for each Slave to all Status modules
        for slaveTWC in self.getSlaveTWCs():
            for module in self.getModulesByType("Status"):
                module["ref"].setStatus(
                    slaveTWC.TWCID,
                    "current_vehicle_vin",
                    "currentVehicleVIN",
                    slaveTWC.currentVIN,
                    "",
                )
            for module in self.getModulesByType("Status"):
                module["ref"].setStatus(
                    slaveTWC.TWCID,
                    "last_vehicle_vin",
                    "lastVehicleVIN",
                    slaveTWC.lastVIN,
                    "",
                )
