import logging
import psycopg2

logger = logging.getLogger(__name__.rsplit(".")[-1])

class TeslaMateVehicle:

    __db_host = None
    __db_name = None
    __db_pass = None
    __db_user = None
    __config = None
    __configConfig = None
    __configTeslaMate = None
    __master = None
    status = None
    syncTokens = False

    def __init__(self, master):
        self.__master = master

        self.__config = master.config
        try:
            self.__configConfig = self.__config["config"]
        except KeyError:
            self.__configConfig = {}
        try:
            self.__configTeslaMate = self.__config["vehicle"]["TeslaMate"]
        except KeyError:
            self.__configTeslaMate = {}

        # Unload if this module is disabled or misconfigured
        if (not self.status):
            self.__master.releaseModule("lib.TWCManager.Vehicle", "TeslaMate")
            return None

        # Configure database parameters
        self.__db_host = self.__configTeslaMate.get("db_host", None)
        self.__db_name = self.__configTeslaMate.get("db_name", None)
        self.__db_pass = self.__configTeslaMate.get("db_pass", None)
        self.__db_user = self.__configTeslaMate.get("db_user", None)

        self.syncTokens = self.__configTeslaMate.get("syncTokens", False)

        # If we're set to sync the auth tokens from the database, do this at startup
        if self.syncTokens:
            self.doSyncTokens()

    def doSyncTokens(self):
        # Connect to TeslaMate database and synchronize API tokens

        if (self.__db_host and self.__db_name and self.__db_user and self.__db_pass):

            conn = psycopg2.connect(
                host=self.__db_host,
                database=self.__db_name,
                user=self.__db_user,
                password=self.__db_pass)

        cur = conn.cursor()

        # Query DB for latest access and refresh token
        cur.execute('SELECT access, refresh, updated_at FROM tokens WHERE id = MAX(id)')

        # Fetch result
        result = cur.fetchone()

        print(result)
