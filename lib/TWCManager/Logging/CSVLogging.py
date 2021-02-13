# CSVLogging module. Provides output to CSV file for regular stats

from datetime import datetime
import logging
import time


class CSVLogging:

    capabilities = {"queryGreenEnergy": False}
    config = None
    configConfig = None
    configLogging = None
    openSessions = {}
    quoteColumns = True
    status = False

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
            self.master.releaseModule("lib.TWCManager.Logging", "CSVLogging")
            return None

        # Initialize the mute config tree if it is not already
        if not self.configLogging.get("mute", None):
            self.configLogging["mute"] = {}

        green_energy_handler = logging.FileHandler(
            self.configLogging["path"] + "/greenenergy.csv"
        )
        green_energy_handler.addFilter(self.green_energy_filter)
        logging.getLogger("").addHandler(green_energy_handler)
        slave_status_handler = logging.FileHandler(
            self.configLogging["path"] + "/slavestatus.csv"
        )
        slave_status_handler.addFilter(self.slave_status_filter)
        logging.getLogger("").addHandler(slave_status_handler)
        charge_sessions_handler = logging.FileHandler(
            self.configLogging["path"] + "/chargesessions.csv"
        )
        charge_sessions_handler.addFilter(self.charge_sessions_filter)
        logging.getLogger("").addHandler(charge_sessions_handler)

    def delimit(self):
        # Return the configured delimiter
        return ","

    def qt(self, string):
        # Perform optional quoting of CSV data
        if self.quoteColumns:
            return '"' + str(string) + '"'
        else:
            return str(string)

    def green_energy_filter(self, record):
        log_type = getattr(record, "logtype", "")
        if log_type != "green_energy" or self.configLogging["mute"].get(
            "GreenEnergy", 0
        ):
            return False

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)

    def message_filter(self, record):
        record.msg = (
            self.qt(int(time.time()))
            + self.delimit()
            + self.qt(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            + self.delimit()
            + self.qt(getattr(record, "genWatts", 0))
            + self.delimit()
            + self.qt(getattr(record, "conWatts", 0))
            + self.delimit()
            + self.qt(getattr(record, "chgWatts", 0))
        )
        record.args = ()
        return True

    def slavePower(self, data):
        # FIXME: remove function
        # Check if this status is muted
        if self.configLogging["mute"].get("SlavePower", 0):
            return None

        # Not Yet Implemented
        return None

    def slaveStatus(self, data):
        # FIXME: remove function
        # Check if this status is muted
        if self.configLogging["mute"].get("SlaveStatus", 0):
            return None

        # Otherwise, write to the CSV
        csv = open(self.configLogging["path"] + "/slavestatus.csv", "a+")
        csv.write(
            self.qt("%02X%02X" % (data["TWCID"][0], data["TWCID"][1]))
            + self.delimit()
            + self.qt(int(time.time()))
            + self.delimit()
            + self.qt(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            + self.delimit()
            + self.qt(data["kWh"])
            + self.delimit()
            + self.qt(data["voltsPerPhase"][0])
            + self.delimit()
            + self.qt(data["voltsPerPhase"][1])
            + self.delimit()
            + self.qt(data["voltsPerPhase"][2])
            + "\n"
        )

    def slave_status_filter(self, record):
        log_type = getattr(record, "logtype", "")
        if log_type != "slave_status" or self.configLogging["mute"].get(
            "SlaveStatus", 0
        ):
            return False

        record.msg = (
            self.qt(
                "%02X%02X" % (getattr(record, "TWCID")[0], getattr(record, "TWCID")[1])
            )
            + self.delimit()
            + self.qt(int(time.time()))
            + self.delimit()
            + self.qt(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            + self.delimit()
            + self.qt(getattr(record, "kWh"))
            + self.delimit()
            + self.qt(getattr(record, "voltsPerPhase")[0])
            + self.delimit()
            + self.qt(getattr(record, "voltsPerPhase")[1])
            + self.delimit()
            + self.qt(getattr(record, "voltsPerPhase")[2])
        )
        record.args = ()
        return True

    def startChargeSession(self, data):
        # FIXME: remove function
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][1])

        # Store the open charging session in memory.
        self.openSessions[data["TWCID"]] = {
            "startTime": data.get("startTime", 0),
            "startFormat": data.get("startFormat", ""),
            "startkWh": data.get("startkWh", 0),
        }

    def stopChargeSession(self, data):
        # FIXME: remove function
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
            self.qt(twcid)
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("startTime", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("startFormat", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("startkWh", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("endTime", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("endFormat", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("endkWh", 0))
            + self.delimit()
            + self.qt(self.openSessions[data["TWCID"]].get("vehicleVIN", ""))
            + "\n"
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

    def charge_sessions_filter(self, record):
        log_type = getattr(record, "logtype", "")
        # Check if this status is muted or it is not the correct log type
        if log_type != "charge_sessions" or self.configLogging["mute"].get(
            "ChargeSessions", 0
        ):
            return False
        charge_state = getattr(record, "chargestate", "")
        if charge_state == "start":
            # Called when a Charge Session Starts.
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )

            # Store the open charging session in memory.
            self.openSessions[getattr(record, "TWCID")] = {
                "startTime": getattr(record, "startTime", 0),
                "startFormat": getattr(record, "startFormat", ""),
                "startkWh": getattr(record, "startkWh", 0),
            }
            return False
        elif charge_state == "update":
            # Called when additional information needs to be updated for a
            # charge session
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )

            # Update the open charging session in memory.
            if getattr(record, "vehicleVIN", None):
                self.openSessions[getattr(record, "TWCID")]["vehicleVIN"] = getattr(
                    record, "vehicleVIN", ""
                )
            return False
        elif charge_state == "stop":
            # Called when a Charge Session Ends.
            # Write the charge session data to CSV
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )

            # Update the open charging session in memory.
            self.openSessions[getattr(record, "TWCID")]["endTime"] = getattr(
                record, "endTime", 0
            )
            self.openSessions[getattr(record, "TWCID")]["endFormat"] = getattr(
                record, "endFormat", 0
            )
            self.openSessions[getattr(record, "TWCID")]["endkWh"] = getattr(
                record, "endkWh", 0
            )

            record.msg = (
                self.qt(twcid)
                + self.delimit()
                + self.qt(
                    self.openSessions[getattr(record, "TWCID")].get("startTime", 0)
                )
                + self.delimit()
                + self.qt(
                    self.openSessions[getattr(record, "TWCID")].get("startFormat", 0)
                )
                + self.delimit()
                + self.qt(
                    self.openSessions[getattr(record, "TWCID")].get("startkWh", 0)
                )
                + self.delimit()
                + self.qt(self.openSessions[getattr(record, "TWCID")].get("endTime", 0))
                + self.delimit()
                + self.qt(
                    self.openSessions[getattr(record, "TWCID")].get("endFormat", 0)
                )
                + self.delimit()
                + self.qt(self.openSessions[getattr(record, "TWCID")].get("endkWh", 0))
                + self.delimit()
                + self.qt(
                    self.openSessions[getattr(record, "TWCID")].get("vehicleVIN", "")
                )
            )
            record.args = ()
            return True
        return False
