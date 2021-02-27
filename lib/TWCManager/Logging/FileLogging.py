# ConsoleLogging module. Provides output to console for logging.

from sys import modules
import logging
from logging.handlers import TimedRotatingFileHandler
from ww import f
import re


class FileLogging:

    capabilities = {
      "queryGreenEnergy": False
    }
    config = None
    configConfig = None
    configLogging = None
    status = True
    logger = None
    mute = {}
    muteDebugLogLevelGreaterThan = 1

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configLogging = master.config["logging"]["FileLogger"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if not self.status:
            self.master.releaseModule("lib.TWCManager.Logging", "FileLogging")
            return None

        # Initialize the mute config tree if it is not already
        self.mute = self.configLogging.get("mute", {})
        self.muteDebugLogLevelGreaterThan = self.mute.get("DebugLogLevelGreaterThan", 1)

        # Initialize Logger
        self.logger = logging.getLogger("TWCManager")
        self.logger.setLevel(logging.INFO)
        handler = TimedRotatingFileHandler(
            self.configLogging.get("path", "/etc/twcmanager/log") + "/logfile",
            when="H",
            interval=1,
            backupCount=24,
        )
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        self.logger.addHandler(handler)

    def debugLog(self, logdata):
        # debugLog is something of a catch-all if we don't have a specific
        # logging function for the given data. It allows a log entry to be
        # passed to us for storage.
        if self.muteDebugLogLevelGreaterThan >= logdata["minLevel"]:
            self.logger.info(
                logdata["function"]
                + " %02d " % logdata["minLevel"]
                + self.escape_ansi(logdata["message"])
            )
        return

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)

    def escape_ansi(self, line):
        ansi_escape = re.compile(r"(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]")
        return ansi_escape.sub("", line)

    def writeLog(self, functionName, message):
        self.debugLog(
            {
                "function": functionName,
                "minLevel": 0,
                "message": message,
            }
        )

    def greenEnergy(self, data):
        # Check if this status is muted
        if self.mute.get("GreenEnergy", 0):
            return None

        self.writeLog(
            "TWCManager",
            f(
                "Green energy generates {data.get('genWatts', 0):.0f}W, Consumption {data.get('conWatts', 0):.0f}W, Charger Load {data.get('chgWatts', 0):.0f}W"
            ),
        )

    def slavePower(self, data):
        # Not yet implemented
        return None

    def slaveStatus(self, data):
        # Check if this status is muted
        if self.mute.get("SlaveStatus", 0):
            return None

        self.writeLog(
            "TWCManager",
            "Slave TWC %02X%02X: Delivered %d kWh, voltage per phase: (%d, %d, %d)."
            % (
                data["TWCID"][0],
                data["TWCID"][1],
                data["kWh"],
                data["voltsPerPhase"][0],
                data["voltsPerPhase"][1],
                data["voltsPerPhase"][2],
            ),
        )

    def startChargeSession(self, data):
        # Check if this status is muted
        if self.mute.get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        self.writeLog("TWCManager", "Charge Session Started for Slave TWC %s" % twcid)

    def stopChargeSession(self, data):
        # Check if this status is muted
        if self.mute.get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Ends.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        self.writeLog("TWCManager", "Charge Session Stopped for Slave TWC %s" % twcid)

    def updateChargeSession(self, data):
        # Check if this status is muted
        if self.mute.get("ChargeSessions", 0):
            return None

        # Called when additional information needs to be updated for a
        # charge session. For console output, we ignore this.
        return None
