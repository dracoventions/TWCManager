# SQLiteLogging module. Provides output to SQLite Database for regular stats
import logging


class SQLiteHandler(logging.Handler):

    def __init__(self, conn):
        logging.Handler.__init__(self)
        self.conn = conn

    def emit(self, record):
        self.format(record)
        charge_state = getattr(record, "chargestate", "")
        if charge_state == "start":
            # Called when a Charge Session Starts.
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )

            query = "INSERT INTO charge_sessions (startTime, startkWh, TWCID) values (?,?,?)"
            self.conn.execute(
                query,
                (
                    getattr(record, "startTime", 0),
                    getattr(record, "startkWh", 0),
                    twcid,
                ),
            )
            self.conn.commit()
        elif charge_state == "update":
            # Called when additional information needs to be updated for a
            # charge session
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )

            # Update the open charging session in memory.
            if getattr(record, "vehicleVIN", None):
                query = "UPDATE charge_sessions SET vehicleVIN = ? WHERE TWCID = ?"
                self.conn.execute(query, (getattr(record, "vehicleVIN", "")))
                self.conn.commit()
        elif charge_state == "stop":
            # Called when a Charge Session Ends.
            twcid = "%02X%02X" % (
                getattr(record, "TWCID")[0],
                getattr(record, "TWCID")[1],
            )
            query = "UPDATE charge_sessions SET endTime = ?, endkWh = ? WHERE TWCID = ?"
            self.conn.execute(
                query,
                (getattr(record, "endTime", 0), getattr(record, "endkWh", 0), twcid),
            )
            self.conn.commit()


class SQLiteLogging:

    capabilities = {"queryGreenEnergy": True}
    config = None
    configConfig = None
    configLogging = None
    db = None
    status = False

    def __init__(self, master):
        self.master = master
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configLogging = master.config["logging"]["SQLite"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if not self.status or not self.configLogging.get("path", None):
            self.master.releaseModule("lib.TWCManager.Logging", "SQLiteLogging")
            return None

        # Initialize the mute config tree if it is not already
        if not self.configLogging.get("mute", None):
            self.configLogging["mute"] = {}

        # Import sqlite module if module is not released
        import sqlite3

        self.conn = sqlite3.connect(self.configLogging["path"])

        # Make sure schema has been created
        self.createSchema()

        charge_sessions_handler = SQLiteHandler(self.conn)
        charge_sessions_handler.addFilter(self.charge_sessions_filter)
        logging.getLogger("").addHandler(charge_sessions_handler)

    def createSchema(self):
        # Initialize the database schema for a database that does not
        # yet exist
        query = """
          CREATE TABLE IF NOT EXISTS charge_sessions (
            startTime int,
            startkWh int,
            TWCID varchar(4),
            endTime int,
            endkWh int,
            vehicleVIN varchar(17),
            primary key(startTime, TWCID)
          );
        """
        self.conn.execute(query)
        self.conn.commit()

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)

    def charge_sessions_filter(self, record):
        log_type = getattr(record, "logtype", "")
        # Check if this status is muted or it is not the correct log type
        if log_type != "charge_sessions" or self.configLogging["mute"].get(
            "ChargeSessions", 0
        ):
            return False
        return True
