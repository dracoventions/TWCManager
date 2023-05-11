# ConsoleLogging module. Provides output to console for logging.
import logging

import sys
from termcolor import colored


logger = logging.getLogger(__name__.rsplit(".")[-1])


class ColorFormatter(logging.Formatter):
    def format(self, record):
        if hasattr(record, "colored"):
            old_args = record.args
            record.args = tuple(colored(arg, record.colored) for arg in record.args)
            s = super(ColorFormatter, self).format(record)
            record.args = old_args
        else:
            s = super(ColorFormatter, self).format(record)
        return s


class ConsoleLogging:
    capabilities = {"queryGreenEnergy": False}
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

        # Initialize Logger
        handler = logging.StreamHandler(sys.stdout)
        if self.configLogging.get("simple", False):
            handler.setFormatter(
                logging.Formatter("%(name)-10.10s %(levelno)02d %(message)s")
            )
        else:
            color_formatter = ColorFormatter(
                colored("%(asctime)s", "yellow")
                + " "
                + colored("%(name)-10.10s", "green")
                + " "
                + colored("%(levelno)d", "cyan")
                + " %(message)s",
                "%H:%M:%S",
            )
            handler.setFormatter(color_formatter)
        # handler.setLevel(logging.INFO)
        logging.getLogger("").addHandler(handler)

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)
