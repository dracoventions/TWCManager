# ConsoleLogging module. Provides output to console for logging.

from sys import modules
from termcolor import colored
from ww import f


class ConsoleLogging:

    config = None
    configConfig = None
    configLogging = None
    status = True

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configLogging = master.config["logging"]["Console"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", True)

        # Unload if this module is disabled or misconfigured
        if not self.status:
            self.master.releaseModule("lib.TWCManager.Logging", "ConsoleLogging")
            return None

        # Initialize the mute config tree if it is not already
        if not self.configLogging.get("mute", None):
            self.configLogging["mute"] = {}

    def debugLog(self, logdata):
        # debugLog is something of a catch-all if we don't have a specific
        # logging function for the given data. It allows a log entry to be
        # passed to us for storage.

        if logdata["debugLevel"] >= logdata["minLevel"]:
            print(
                colored(logdata["logTime"] + " ", "yellow")
                + colored(f("{logdata['function']}"), "green")
                + colored(f(" {logdata['minLevel']} "), "cyan")
                + f("{logdata['message']}")
            )

        return

    def greenEnergy(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("GreenEnergy", 0):
            return None

        genwattsDisplay = f("{data.get('genWatts', 0):.0f}W")
        conwattsDisplay = f("{data.get('conWatts', 0):.0f}W")
        chgwattsDisplay = f("{data.get('chgWatts', 0):.0f}W")

        if self.config["config"]["subtractChargerLoad"]:
            othwatts = data.get('conWatts', 0) - data.get('chgWatts', 0)
            othwattsDisplay = f("{othwatts:.0f}W")
            self.master.debugLog(
                1,
                "TWCManager",
                f(
                    "Green energy generates {colored(genwattsDisplay, 'magenta')}, Consumption {colored(conwattsDisplay, 'magenta')} (Other Load {colored(othwattsDisplay, 'magenta')}, Charger Load {colored(chgwattsDisplay, 'magenta')})"
                ),
            )
        else:
            self.master.debugLog(
                1,
                "TWCManager",
                f(
                    "Green energy generates {colored(genwattsDisplay, 'magenta')}, Consumption {colored(conwattsDisplay, 'magenta')}, Charger Load {colored(chgwattsDisplay, 'magenta')}"
                ),
            )

    def slavePower(self, data):
        # Not yet implemented
        return None

    def slaveStatus(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("SlaveStatus", 0):
            return None

        self.master.debugLog(
            1,
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
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        self.master.debugLog(
            1, "TWCManager", "Charge Session Started for Slave TWC %s" % twcid
        )

    def stopChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Ends.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        self.master.debugLog(
            1, "TWCManager", "Charge Session Stopped for Slave TWC %s" % twcid
        )

    def updateChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when additional information needs to be updated for a
        # charge session. For console output, we ignore this.
        return None
