# CSVLogging module. Provides output to CSV file for regular stats

import logging


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
        green_energy_formatter = logging.Formatter(
            self.qt("%(created)d")
            + self.delimit()
            + self.qt("%(asctime)s")
            + self.delimit()
            + self.qt("%(genWatts).1f")
            + self.delimit()
            + self.qt("%(conWatts).1f")
            + self.delimit()
            + self.qt("%(chgWatts).1f"),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        green_energy_handler.setFormatter(green_energy_formatter)
        logging.getLogger("").addHandler(green_energy_handler)

        slave_status_handler = logging.FileHandler(
            self.configLogging["path"] + "/slavestatus.csv"
        )
        slave_status_handler.addFilter(self.slave_status_filter)
        slave_status_formatter = logging.Formatter(
            self.qt("{TWCID[0]:02X}{TWCID[1]:02X}")
            + self.delimit()
            + self.qt("{created:.0f}")
            + self.delimit()
            + self.qt("{asctime:s}")
            + self.delimit()
            + self.qt("{kWh:d}")
            + self.delimit()
            + self.qt("{voltsPerPhase[0]:d}")
            + self.delimit()
            + self.qt("{voltsPerPhase[1]:d}")
            + self.delimit()
            + self.qt("{voltsPerPhase[2]:d}"),
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )
        slave_status_handler.setFormatter(slave_status_formatter)
        logging.getLogger("").addHandler(slave_status_handler)

        charge_sessions_handler = logging.FileHandler(
            self.configLogging["path"] + "/chargesessions.csv"
        )
        charge_sessions_handler.addFilter(self.charge_sessions_filter)
        charge_sessions_formatter = logging.Formatter(
            self.qt("{TWCID[0]:02X}{TWCID[1]:02X}")
            + self.delimit()
            + self.qt("{startTime:d}")
            + self.delimit()
            + self.qt("{startFormat:s}")
            + self.delimit()
            + self.qt("{startkWh:d}")
            + self.delimit()
            + self.qt("{endTime:d}")
            + self.delimit()
            + self.qt("{endFormat:s}")
            + self.delimit()
            + self.qt("{endkWh:d}")
            + self.delimit()
            + self.qt("{vehicleVIN:s}"),
            style="{",
        )
        charge_sessions_handler.setFormatter(charge_sessions_formatter)
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

    def slave_status_filter(self, record):
        log_type = getattr(record, "logtype", "")
        if log_type != "slave_status" or self.configLogging["mute"].get(
            "SlaveStatus", 0
        ):
            return False
        return True

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
            record.startTime = self.openSessions[getattr(record, "TWCID")].get(
                "startTime", 0
            )
            record.startFormat = self.openSessions[getattr(record, "TWCID")].get(
                "startFormat", 0
            )
            record.startkWh = self.openSessions[getattr(record, "TWCID")].get(
                "startkWh", 0
            )
            record.endTime = self.openSessions[getattr(record, "TWCID")].get(
                "endTime", 0
            )
            record.endFormat = self.openSessions[getattr(record, "TWCID")].get(
                "endFormat", 0
            )
            record.endkWh = self.openSessions[getattr(record, "TWCID")].get("endkWh", 0)
            record.vehicleVIN = self.openSessions[getattr(record, "TWCID")].get(
                "vehicleVIN", ""
            )
            return True
        return False
