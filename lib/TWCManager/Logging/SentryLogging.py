# SentryLogging module. Provides output to console for logging.
import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SentryLogging:
    capabilities = {"queryGreenEnergy": False}
    config = None
    configConfig = None
    configLogging = None
    status = True
    logger = None
    mute = {}
    muteDebugLogLevelGreaterThan = 1

    def __init__(self, master):
        # raise ImportError
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configLogging = master.config["logging"]["Sentry"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", False)
        self.dsn = self.configLogging.get("DSN", False)

        # Unload if this module is disabled or misconfigured
        if not self.status or not self.dsn:
            self.master.releaseModule("lib.TWCManager.Logging", "SentryLogging")
            return None

        # Initialize the mute config tree if it is not already
        self.mute = self.configLogging.get("mute", {})
        self.muteDebugLogLevelGreaterThan = self.mute.get("DebugLogLevelGreaterThan", 1)

        # Initialize Logger
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )
        sentry_sdk.init(self.dsn, integrations=[sentry_logging], traces_sample_rate=1.0)

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)
