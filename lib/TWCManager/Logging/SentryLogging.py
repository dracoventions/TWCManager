# SentryLogging module. Provides output to console for logging.
import logging

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

import re


logger = logging.getLogger(__name__.rsplit(".")[-1])


class SentryLogging:

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
        sentry_sdk.init(
            self.dsn,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,
        )

    def slavePower(self, data):
        # FIXME: remove function
        return None

    def slaveStatus(self, data):
        # FIXME: remove function
        return

    def startChargeSession(self, data):
        # FIXME: remove function
        return

    def stopChargeSession(self, data):
        # FIXME: remove function
        return

    def updateChargeSession(self, data):
        # FIXME: remove function
        return
