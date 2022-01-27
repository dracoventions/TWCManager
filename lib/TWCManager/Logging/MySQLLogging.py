# MySQLLogging module. Provides output to a MySQL Server for regular statistics
# recording.
import logging


logger = logging.getLogger(__name__.rsplit(".")[-1])


class MySQLHandler(logging.Handler):
    slaveSession = {}

    def __init__(self, db):

        logging.Handler.__init__(self)
        self.db = db

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
                self.slaveSession[twcid] = getattr(record, "startTime", 0)

                query = """
                    INSERT INTO charge_sessions (chargeid, startTime, startkWh, slaveTWC)
                    VALUES (%s,now(),%s,'%s')
                """

                # Ensure database connection is alive, or reconnect if not
                try:
                    self.db.ping(reconnect=True)
                except pymysql.err.OperationalError as e:
                    logger.info("Error connecting to MySQL database. %s", str(e))
                    return

                cur = self.db.cursor()
                rows = 0
                try:
                    rows = cur.execute(
                        query,
                        (
                            getattr(record, "startTime", 0),
                            getattr(record, "startkWh", 0),
                            twcid,
                        ),
                    )
                except Exception as e:
                    logger.error("Error updating MySQL database: %s", e)
                if rows:
                    # Query was successful. Commit
                    self.db.commit()
                else:
                    # Issue, log message and rollback
                    logger.info("Error updating MySQL database. Rows = %d", rows)
                    self.db.rollback()
                cur.close()
            elif charge_state == "update":
                # Called when additional information needs to be updated for a
                # charge session
                twcid = "%02X%02X" % (
                    getattr(record, "TWCID")[0],
                    getattr(record, "TWCID")[1],
                )
                chgid = self.slaveSession.get(twcid, 0)
                if getattr(record, "vehicleVIN", None):
                    query = """
                        UPDATE charge_sessions SET vehicleVIN = '%s'
                        WHERE chargeid = %s AND slaveTWC = '%s'
                    """

                    # Ensure database connection is alive, or reconnect if not
                    try:
                        self.db.ping(reconnect=True)
                    except pymysql.err.OperationalError as e:
                        logger.info("Error connecting to MySQL database. %s", str(e))
                        return

                    cur = self.db.cursor()
                    rows = 0
                    try:
                        rows = cur.execute(
                            query % (getattr(record, "vehicleVIN", ""), chgid, twcid)
                        )
                    except Exception as e:
                        logger.error("Error updating MySQL database: %s", e)
                    if rows:
                        # Query was successful. Commit
                        self.db.commit()
                    else:
                        # Issue, log message and rollback
                        self.db.rollback()
                    cur.close()
            elif charge_state == "stop":
                # Called when a Charge Session Ends.
                twcid = "%02X%02X" % (
                    getattr(record, "TWCID")[0],
                    getattr(record, "TWCID")[1],
                )
                chgid = self.slaveSession.get(twcid, 0)
                query = """
                    UPDATE charge_sessions SET endTime = now(), endkWh = %s
                    WHERE chargeid = %s AND slaveTWC = '%s'
                """

                # Ensure database connection is alive, or reconnect if not
                try:
                    self.db.ping(reconnect=True)
                except pymysql.err.OperationalError as e:
                    logger.info("Error connecting to MySQL database. %s", str(e))
                    return

                cur = self.db.cursor()
                rows = 0
                try:
                    rows = cur.execute(
                        query,
                        (
                            getattr(record, "endkWh", 0),
                            chgid,
                            twcid,
                        ),
                    )
                except Exception as e:
                    logger.error("Error updating MySQL database: %s", e)
                if rows:
                    # Query was successful. Commit
                    self.db.commit()
                else:
                    # Issue, log message and rollback
                    logger.error("Error updating MySQL database. Rows = %d", rows)
                    self.db.rollback()
                cur.close()
                self.slaveSession[twcid] = 0
        elif log_type == "green_energy":
            # Ensure database connection is alive, or reconnect if not
            try:
                self.db.ping(reconnect=True)
            except pymysql.err.OperationalError as e:
                logger.info("Error connecting to MySQL database. %s", str(e))
                return

            query = """
                INSERT INTO green_energy (time, genW, conW, chgW)
                VALUES (now(), %s, %s, %s)
            """

            cur = self.db.cursor()
            rows = 0
            try:
                rows = cur.execute(
                    query,
                    (
                        getattr(record, "genWatts", 0),
                        getattr(record, "conWatts", 0),
                        getattr(record, "chgWatts", 0),
                    ),
                )
            except Exception as e:
                logger.error("Error updating MySQL database: %s", e)
            if rows:
                # Query was successful. Commit
                self.db.commit()
            else:
                # Issue, log message and rollback
                logger.info("Error updating MySQL database. Rows = %d" % rows)
                self.db.rollback()
            cur.close()


class MySQLLogging:

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
            self.configLogging = master.config["logging"]["MySQL"]
        except KeyError:
            self.configLogging = {}
        self.status = self.configLogging.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if not self.status or not self.configLogging.get("host", None):
            self.master.releaseModule("lib.TWCManager.Logging", "MySQLLogging")
            return None

        # Initialize the mute config tree if it is not already
        if not self.configLogging.get("mute", None):
            self.configLogging["mute"] = {}

        # Import MySQL module if module is not released
        global pymysql
        import pymysql

        try:
            self.db = pymysql.connect(
                host=self.configLogging.get("host", ""),
                port=self.configLogging.get("port", 3306),
                user=self.configLogging.get("username", ""),
                password=self.configLogging.get("password", ""),
                database=self.configLogging.get("database", ""),
            )
        except pymysql.err.OperationalError as e:
            logger.info("Error connecting to MySQL database")
            logger.info(str(e))
        else:
            mysql_handler = MySQLHandler(db=self.db)
            mysql_handler.addFilter(self.mysql_filter)
            logging.getLogger("").addHandler(mysql_handler)

    def getCapabilities(self, capability):
        # Allows query of module capabilities when deciding which Logging module to use
        return self.capabilities.get(capability, False)

    def mysql_filter(self, record):
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

        # Ensure database connection is alive, or reconnect if not
        try:
            self.db.ping(reconnect=True)
        except pymysql.err.OperationalError as e:
            logger.info("Error connecting to MySQL database. %s", str(e))
            return

        query = """
            SELECT * from green_energy where time>%s and time<%s
        """
        cur = self.db.cursor()
        rows = 0
        result = {}
        try:
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
                logger.error("Error query MySQL database. Rows = %d", rows)
            cur.close()
        return list(result)

    def slaveStatus(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("SlaveStatus", 0):
            return None

        # Ensure database connection is alive, or reconnect if not
        try:
            self.db.ping(reconnect=True)
        except pymysql.err.OperationalError as e:
            logger.info("Error connecting to MySQL database. %s", str(e))
            return

        # Otherwise, add to database
        cursor = self.db.cursor()
        query = """
            INSERT INTO slave_status (slaveTWC, time, kWh, voltsPhaseA,
            voltsPhaseB, voltsPhaseC)
            VALUES (%s, now(), %s, %s, %s, %s);
        """
        rows = 0
        try:
            rows = cursor.execute(
                query,
                (
                    "%02X%02X" % (data["TWCID"][0], data["TWCID"][1]),
                    data["kWh"],
                    data["voltsPerPhase"][0],
                    data["voltsPerPhase"][1],
                    data["voltsPerPhase"][2],
                ),
            )
        except Exception as e:
            logger.info("Error updating MySQL database")
            logger.info(str(e))
        if rows:
            # Query was successful. Commit
            self.db.commit()
        else:
            # Issue, log message and rollback
            logger.info("Error updating MySQL database. Rows = %d" % rows)
            self.db.rollback()
        cursor.close()
