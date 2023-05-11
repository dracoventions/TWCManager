# SQLiteLogging module. Provides output to SQLite Database for regular stats
import logging

logger = logging.getLogger(__name__.rsplit(".")[-1])


class SQLiteHandler(logging.Handler):
    def __init__(self, db):
        logging.Handler.__init__(self)
        self.db = db
        # Initialize the database schema for a database that does not
        # yet exist
        query_charge_sessions = """
          CREATE TABLE IF NOT EXISTS charge_sessions (
              chargeid int,
              startTime timestamp,
              startkWh int,
              slaveTWC varchar(4),
              endTime datetime,
              endkWh int,
              vehicleVIN varchar(17),
              primary key(startTime, slaveTWC)
          );
        """
        query_green_energy = """
          CREATE TABLE IF NOT EXISTS green_energy (
            time timestamp,
            genW DECIMAL(9,3),
            conW DECIMAL(9,3),
            chgW DECIMAL(9,3),
            primary key(time)
          );
        """
        query_slave_status = """
          CREATE TABLE IF NOT EXISTS slave_status (
            slaveTWC varchar(4),
            time timestamp,
            kWh int,
            voltsPhaseA int,
            voltsPhaseB int,
            voltsPhaseC int,
            primary key (slaveTWC, time)
          );
        """

        conn = None
        try:
            conn = sqlite3.connect(self.db, uri=True)
        except sqlite3.OperationalError as e:
            logger.exception("Error Opening SQLite3 Databaase: %s", e)

        if conn:
            conn.execute(query_charge_sessions)
            conn.execute(query_green_energy)
            conn.execute(query_slave_status)
            conn.commit()
        else:
            logger.error("SQLite connection is null")

    def emit(self, record):
        self.format(record)
        log_type = getattr(record, "logtype", "")
        if log_type == "charge_sessions":
            charge_state = getattr(record, "chargestate", "")
            if charge_state == "start":
                # Called when a Charge Session Starts.
                twcid = "%02X%02X" % (
                    getattr(record, "TWCID")[0],
                    getattr(record, "TWCID")[1],
                )

                query = "INSERT INTO charge_sessions (startTime, startkWh, slaveTWC) values (?,?,?)"
                conn = sqlite3.connect(self.db, uri=True)
                conn.execute(
                    query,
                    (
                        getattr(record, "startTime", 0),
                        getattr(record, "startkWh", 0),
                        twcid,
                    ),
                )
                conn.commit()
            elif charge_state == "update":
                # Called when additional information needs to be updated for a
                # charge session
                twcid = "%02X%02X" % (
                    getattr(record, "TWCID")[0],
                    getattr(record, "TWCID")[1],
                )

                # Update the open charging session in memory.
                if getattr(record, "vehicleVIN", None):
                    query = (
                        "UPDATE charge_sessions SET vehicleVIN = ? WHERE slaveTWC = ?"
                    )
                    conn = sqlite3.connect(self.db, uri=True)
                    conn.execute(query, (getattr(record, "vehicleVIN", "")))
                    conn.commit()
            elif charge_state == "stop":
                # Called when a Charge Session Ends.
                twcid = "%02X%02X" % (
                    getattr(record, "TWCID")[0],
                    getattr(record, "TWCID")[1],
                )
                query = "UPDATE charge_sessions SET endTime = ?, endkWh = ? WHERE slaveTWC = ?"
                conn = sqlite3.connect(self.db, uri=True)
                conn.execute(
                    query,
                    (
                        getattr(record, "endTime", 0),
                        getattr(record, "endkWh", 0),
                        twcid,
                    ),
                )
                conn.commit()
        elif log_type == "green_energy":
            query = """
                INSERT INTO green_energy (time, genW, conW, chgW)
                VALUES (datetime('now'), ?, ?, ?)
            """

            rows = 0
            try:
                conn = sqlite3.connect(self.db, uri=True)
                rows = conn.execute(
                    query,
                    (
                        getattr(record, "genWatts", 0),
                        getattr(record, "conWatts", 0),
                        getattr(record, "chgWatts", 0),
                    ),
                )
            except Exception as e:
                logger.info("Error updating SQLite database: %s", e)
            else:
                if rows:
                    # Query was successful. Commit
                    conn.commit()
                else:
                    # Issue, log message and rollback
                    logger.info("Error updating SQLite database. Rows = %d" % rows)
                    conn.rollback()


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

        global sqlite3
        import sqlite3

        self.db = self.configLogging["path"]
        sqlite_handler = SQLiteHandler(db=self.db)
        sqlite_handler.addFilter(self.sqlite_filter)
        logging.getLogger("").addHandler(sqlite_handler)

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)

    def sqlite_filter(self, record):
        log_type = getattr(record, "logtype", "")
        # Check if this status is muted or it is not the correct log type
        if log_type == "charge_sessions" and not self.configLogging["mute"].get(
            "ChargeSessions", 0
        ):
            return True
        # Check if this status is muted or it is not the correct log type
        if log_type == "green_energy" and not self.configLogging["mute"].get(
            "GreenEnergy", 0
        ):
            return True
        # Check if this status is muted or it is not the correct log type
        if log_type == "slave_status" and not self.configLogging["mute"].get(
            "SlaveStatus", 0
        ):
            return True
        return False

    def queryGreenEnergy(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("GreenEnergy", 0):
            return None

        query = """
            SELECT * from green_energy where time > ? and time < ?
        """
        rows = 0
        result = {}
        try:
            conn = sqlite3.connect(
                self.db,
                uri=True,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            cur = conn.cursor()
            rows = cur.execute(
                query, (data.get("dateBegin", 0), data.get("dateEnd", 0))
            )
        except Exception as e:
            logger.exception("Error executing queryGreenEnergy query: %s", e)
        else:
            if rows:
                # Query was successful. Commit
                result = cur.fetchall()
            else:
                # Issue, log message
                logger.error("Error query SQLite database. Rows = %d", rows)
            cur.close()
        return list(result)
