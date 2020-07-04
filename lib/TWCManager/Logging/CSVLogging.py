# CSVLogging module. Provides output to CSV file for regular stats

from datetime import datetime
import time

class CSVLogging:

    config        = None
    configConfig  = None
    configLogging = None
    openSessions  = {}
    quoteColumns  = True
    status        = False

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configLogging = master.config["logging"]["CSV"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if not self.status:
          self.master.releaseModule("lib.TWCManager.Logging","CSVLogging");
          return None

        # Initialize the mute config tree if it is not already
        if not self.configLogging.get("mute", None):
            self.configLogging["mute"] = {}

    def delimit(self):
        # Return the configured delimiter
        return ","

    def greenEnergy(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("GreenEnergy", 0):
            return None

        # Otherwise, write to the CSV
        csv = open(self.configLogging["path"] + "/greenenergy.csv", "a+")
        csv.write(
            self.qt(int(time.time())) +
            self.delimit() +
            self.qt(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +
            self.delimit() +
            self.qt(data.get("genWatts", 0)) +
            self.delimit() +
            self.qt(data.get("conWatts", 0)) +
            self.delimit() +
            self.qt(data.get("chgWatts", 0)) +
            "\n"
        )

    def qt(self, string):
        # Perform optional quoting of CSV data
        if self.quoteColumns:
            return '"' + str(string) + '"'
        else:
            return str(string)

    def slavePower(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("SlavePower", 0):
            return None

        # Not Yet Implemented
        return None

    def slaveStatus(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("SlaveStatus", 0):
            return None

        # Otherwise, write to the CSV
        csv = open(self.configLogging["path"] + "/slavestatus.csv", "a+")
        csv.write(
            self.qt("%02X%02X" % (data["TWCID"][0], data["TWCID"][1])) +
            self.delimit() +
            self.qt(int(time.time())) + 
            self.delimit() +
            self.qt(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) +
            self.delimit() +
            self.qt(data["kWh"]) + 
            self.delimit() +
            self.qt(data["voltsPerPhase"][0]) +
            self.delimit() +
            self.qt(data["voltsPerPhase"][1]) +
            self.delimit() +
            self.qt(data["voltsPerPhase"][2]) +
            "\n"
        )

    def startChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][1])

        # Store the open charging session in memory.
        self.openSessions[data["TWCID"]] = {
          "startTime": data.get("startTime", 0),
          "startFormat": data.get("startFormat", ""),
          "startkWh": data.get("startkWh", 0)
        }

    def stopChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Ends.
        # Write the charge session data to CSV
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][1])

        # Update the open charging session in memory.
        self.openSessions[data["TWCID"]]["endTime"] = data.get("endTime", 0)
        self.openSessions[data["TWCID"]]["endFormat"] = data.get("endFormat", 0)
        self.openSessions[data["TWCID"]]["endkWh"] = data.get("endkWh", 0)

        csv = open(self.configLogging["path"] + "/chargesessions.csv", "a+")
        csv.write(
            self.qt(twcid) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("startTime", 0)) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("startFormat", 0)) +
            self.delimit() + 
            self.qt(self.openSessions[data["TWCID"]].get("startkWh", 0)) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("endTime", 0)) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("endFormat", 0)) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("endkWh", 0)) +
            self.delimit() +
            self.qt(self.openSessions[data["TWCID"]].get("vehicleVIN", "")) + "\n"
        )

    def updateChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when additional information needs to be updated for a
        # charge session
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][1])

        # Update the open charging session in memory.
        if data.get("vehicleVIN", None): 
            self.openSessions[data["TWCID"]]["vehicleVIN"] = data.get("vehicleVIN", "")

