# MySQLLogging module. Provides output to a MySQL Server for regular statistics
# recording.


class MySQLLogging:

    config = None
    configConfig = None
    configLogging = None
    db = None
    slaveSession = {}
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
        import pymysql

        try:
            self.db = pymysql.connect(
                self.configLogging.get("host", ""),
                self.configLogging.get("username", ""),
                self.configLogging.get("password", ""),
                self.configLogging.get("database", ""),
            )
        except pymysql.err.OperationalError as e:
            self.master.debugLog(1, "MySQLLog", "Error connecting to MySQL database")
            self.master.debugLog(1, "MySQLLog", str(e))

    def debugLog(self, logdata):
        # debugLog is something of a catch-all if we don't have a specific
        # logging function for the given data. It allows a log entry to be
        # passed to us for storage.
        return

    def greenEnergy(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("GreenEnergy", 0):
            return None

        # Ensure database connection is alive, or reconnect if not
        self.db.ping(reconnect=True)

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
                    data.get("genWatts", 0),
                    data.get("conWatts", 0),
                    data.get("chgWatts", 0),
                ),
            )
        except Exception as e:
            self.master.debugLog(1, "MySQLLog", "Error updating MySQL database")
            self.master.debugLog(1, "MySQLLog", str(e))
        if rows:
            # Query was successful. Commit
            self.db.commit()
        else:
            # Issue, log message and rollback
            self.master.debugLog(
                1, "MySQLLog", "Error updating MySQL database. Rows = %d" % rows
            )
            self.db.rollback()
        cur.close()

    def queryGreenEnergy(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("GreenEnergy", 0):
            return None
        # Ensure database connection is alive, or reconnect if not
        self.db.ping(reconnect=True)

        query = """
            SELECT * from green_energy where time>%s and time<%s
        """
        cur = self.db.cursor()
        rows = 0
        try:
            rows = cur.execute(
                query,
                (
                    data.get("dateBegin", 0),
                    data.get("dateEnd", 0),
                ),
            )
        except Exception as e:
            self.master.debugLog(1, "MySQLLog", str(e))

        result={}
        if rows:
            # Query was successful. Commit
            result = cur.fetchall()
        else:
            # Issue, log message
            self.master.debugLog(
                1, "MySQLLog", "Error query MySQL database. Rows = %d" % rows
            )
        cur.close()
        return list(result)


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

        # Ensure database connection is alive, or reconnect if not
        self.db.ping(reconnect=True)

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
            self.master.debugLog(1, "MySQLLog", "Error updating MySQL database")
            self.master.debugLog(1, "MySQLLog", str(e))
        if rows:
            # Query was successful. Commit
            self.db.commit()
        else:
            # Issue, log message and rollback
            self.master.debugLog(
                1, "MySQLLog", "Error updating MySQL database. Rows = %d" % rows
            )
            self.db.rollback()
        cursor.close()

    def startChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        self.slaveSession[twcid] = data.get("startTime", 0)
        query = """
            INSERT INTO charge_sessions (chargeid, startTime, startkWh, slaveTWC) 
            VALUES (%s,now(),%s,%s)
        """

        # Ensure database connection is alive, or reconnect if not
        self.db.ping(reconnect=True)

        cur = self.db.cursor()
        rows = 0
        try:
            rows = cur.execute(
                query, (data.get("startTime", 0), data.get("startkWh", 0), twcid)
            )
        except Exception as e:
            self.master.debugLog(1, "MySQLLog", "Error updating MySQL database")
            self.master.debugLog(1, "MySQLLog", str(e))
        if rows:
            # Query was successful. Commit
            self.db.commit()
        else:
            # Issue, log message and rollback
            self.master.debugLog(
                1, "MySQLLog", "Error updating MySQL database. Rows = %d" % rows
            )
            self.db.rollback()
        cur.close()

    def stopChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when a Charge Session Ends.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        chgid = self.slaveSession.get(twcid, 0)
        query = """
            UPDATE charge_sessions SET endTime = now(), endkWh = %s 
            WHERE chargeid = %s AND slaveTWC = %s
        """

        # Ensure database connection is alive, or reconnect if not
        self.db.ping(reconnect=True)

        cur = self.db.cursor()
        rows = 0
        try:
            rows = cur.execute(query, (data.get("endkWh", 0), chgid, twcid))
        except Exception as e:
            self.master.debugLog(1, "MySQLLog", "Error updating MySQL database")
            self.master.debugLog(1, "MySQLLog", str(e))
        if rows:
            # Query was successful. Commit
            self.db.commit()
        else:
            # Issue, log message and rollback
            self.master.debugLog(
                1, "MySQLLog", "Error updating MySQL database. Rows = %d" % rows
            )
            self.db.rollback()
        cur.close()
        self.slaveSession[twcid] = 0

    def updateChargeSession(self, data):
        # Check if this status is muted
        if self.configLogging["mute"].get("ChargeSessions", 0):
            return None

        # Called when additional information needs to be updated for a
        # charge session
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        chgid = self.slaveSession.get(twcid, 0)
        if data.get("vehicleVIN", None):
            query = """
                UPDATE charge_sessions SET vehicleVIN = %s 
                WHERE chargeid = %s AND slaveTWC = %s
            """

            # Ensure database connection is alive, or reconnect if not
            self.db.ping(reconnect=True)

            cur = self.db.cursor()
            rows = 0
            try:
                rows = cur.execute(query, (data.get("vehicleVIN", ""), chgid, twcid))
            except Exception as e:
                self.master.debugLog(1, "MySQLLog", "Error updating MySQL database")
                self.master.debugLog(1, "MySQLLog", str(e))
            if rows:
                # Query was successful. Commit
                self.db.commit()
            else:
                # Issue, log message and rollback
                self.db.rollback()
            cur.close()
        return None
