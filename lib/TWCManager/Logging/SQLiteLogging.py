# SQLiteLogging module. Provides output to SQLite Database for regular stats

class SQLiteLogging:

    config        = None
    configConfig  = None
    configLogging = None
    db            = None
    status        = False

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
        if (not self.status or not self.configLogging.get("path", None)):
          self.master.releaseModule("lib.TWCManager.Logging","SQLiteLogging");
          return None

        # Import sqlite module if module is not released
        import sqlite3
        self.db = sqlite3.connect(self.configLogging["path"])

        # Check if the database schema has been applied
        if (not self.checkTable("charge_sessions")):
            self.createSchema()

    def checkTable(self, tableName):
        # Confirm if a given table exists within the schema
        query = "SELECT name FROM sqlite_master WHERE type='table' "
        query += "AND name = ?"

        cur = self.db.cursor()
        cur.execute(query, (tableName))
        cur.close()

    def createSchema(self):
        # Initialize the database schema for a database that does not
        # yet exist
        query = """
          CREATE TABLE charge_sessions (
            startTime int,
            startkWh int,
            TWCID varchar(4),
            endTime int,
            endkWh int,
            vehicleVIN varchar(17),
            primary key(startTime, TWCID)
          );
        """

    def slavePower(self, data):
        # Not Yet Implemented
        return None

    def slaveStatus(self, data):
        # Not yet implemented
        return None

    def startChargeSession(self, data):
        # Called when a Charge Session Starts.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        query = "INSERT INTO charge_sessions (startTime, startkWh, TWCID) values (?,?,?)"
        cur = self.db.cursor()
        cur.execute(query, (data.get("startTime", 0),
           data.get("startkWh", 0), twcid))
        cur.close()

    def stopChargeSession(self, data):
        # Called when a Charge Session Ends.
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        query = "UPDATE charge_sessions SET endTime = ?, endkWh = ? WHERE TWCID = ?"
        cur = self.db.cursor()
        cur.execute(query, (data.get("endTime", 0),
           data.get("endkWh", 0), twcid))
        cur.close()

    def updateChargeSession(self, data):
        # Called when additional information needs to be updated for a
        # charge session
        twcid = "%02X%02X" % (data["TWCID"][0], data["TWCID"][0])
        if data.get("vehicleVIN", None):
            query = "UPDATE charge_sessions SET vehicleVIN = ? WHERE TWCID = ?"
            cur = self.db.cursor()
            cur.execute(query, (data.get("vehicleVIN", "")))
            cur.close()
        return None
