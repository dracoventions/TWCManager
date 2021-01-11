# Kostal Modbus interface for realtime solar data
# written by Andreas Hopfenblatt in Q4/2020.
# Contact: hopfi2k@me.com
# Tested with Kostal Plenticore Hybrid 10 inverter
# should work with other Kostal inverters too
# connects only via ModBus TCP to the inverter
# use on your own risk
#
import socket


class Kostal:
    import time
    from pyModbusTCP import utils
    from pyModbusTCP.client import ModbusClient

    cacheTime = 10              # in seconds
    config = None
    configConfig = None
    configKostal = None
    debugLevel = 0
    fetchFailed = False
    lastFetch = 0
    master = None
    serverIP = None
    serverPort = 80
    enabled = False
    timeout = 10
    voltage = 0
    totalDCPower = 0
    home_fromGrid = 0
    home_fromSolar = 0
    inverterType = ""
    inverterIP = ""
    m_client = None

    def __init__(self, master):
        self.master = master
        self.config = master.config

        # try to read the config file
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}

        # try to read values from the config file
        try:
            self.configKostal = master.config["sources"]["Kostal"]
        except KeyError:
            self.configKostal = {}

        # initialize variables
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.enabled = self.configKostal.get("enabled", False)
        self.serverIP = self.configKostal.get("serverIP", None)
        self.modbusPort = int(self.configKostal.get("modbusPort", 1502))
        self.unitID = int(self.configKostal.get("unitID", 71))

        # Unload if this module is disabled or not properly configured
        if (not self.enabled) or (not self.canConnect()):
            self.master.debugLog(
                1,
                'Kostal',
                'Error connecting to Kostal Inverter. Please check your configuration!'
            )
            self.master.releaseModule("lib.TWCManager.EMS", "Kostal")

        # module successfully loaded, provide general inverter data
        else:
            self.update()

    # check if connection via ModBusTCP is possible
    def canConnect(self):
        try:
            sock = socket.create_connection((self.serverIP, self.modbusPort), timeout=1)

        except socket.timeout as err:
            self.master.debugLog(1, 'Kostal', 'Timeout connecting to Kostal Inverter. Please check your configuration!')
            return False
        except socket.error as err:
            self.master.debugLog(1, 'Kostal', 'ERROR connecting to Kostal Inverter. Please check your configuration!')
            return False

        # successfully connected to the inverter
        return True

    # read registers directly from the inverter via Modbus protocol
    def readModbus(self, register, data_format="Float", data_length=2):
        # check if ModBus connection is established, and create one if not
        if self.m_client is None:
            try:
                # open Modbus connection for reading
                self.m_client = self.ModbusClient(
                    self.serverIP,
                    port=self.modbusPort,
                    unit_id=self.unitID,
                    auto_open=True
                )
            except ValueError:
                self.master.debugLog(
                    1,
                    'Kostal',
                    'Error connection to Kostal ModBus interface. Pls. check your config!'
                )
                self.fetchFailed = True
                return False

        # depending on expected data format, read the modbus registers
        if data_format == "Float" and data_length == 2:
            # read the given modbus register as float, big endian coded, 2 bytes
            data_raw = self.m_client.read_holding_registers(register, data_length)

            # if we received any data, process it and return the converted value
            if data_raw:
                return float(self.utils.decode_ieee((data_raw[1] << 16) + data_raw[0]))

        elif data_format == "String" and (data_length == 8 or data_length == 32):
            # read a string from the modbus register with the given length
            # kostal modbus strings are either 8 or 16 bytes long
            data_raw = self.m_client.read_holding_registers(register, data_length-1)
            if not data_raw:
                return False

            data_string = ""
            for value in data_raw:
                hex_value = str(hex(value)[2:])
                left = int(str(hex_value)[:2], 16)
                right = int(str(hex_value)[-2:], 16)
                data_string += chr(left) + chr(right)

            # check if we really received a string and return it
            if data_raw and data_string:
                self.fetchFailed = True
                return str(data_string)

        # if all failed, return false
        return False

    # update the power currently produced by the inverter
    # by reading register 100
    def updateTotalDCPower(self):
        self.totalDCPower = self.readModbus(100)
        self.master.debugLog(
            10,
            'Kostal',
            'Total Solar Power available: {:.2f} W'.format(self.totalDCPower)
        )

    # update the house consumption from the grid
    # by reading register 108
    def updateHomeFromGrid(self):
        self.home_fromGrid = self.readModbus(108)
        self.master.debugLog(
            10,
            'Kostal',
            'Home consumption from Grid: {:.2f} W'.format(self.home_fromGrid)
        )

    # update the house consumption from solar
    # by reading register 116
    def updateHomeFromSolar(self):
        self.home_fromSolar = self.readModbus(116)
        self.master.debugLog(
            10,
            'Kostal',
            'Home consumption from Solar: {:.2f} W'.format(self.home_fromSolar)
        )

    # determine the inverter model (type) and the IP it's connected to
    # by reading register 768 (model) and 420 (IP)
    def getInverterType(self):
        self.inverterType = None
        self.inverterType = self.readModbus(768, "String", 32)
        self.inverterIP = self.readModbus(420, "String", 8)
        self.master.debugLog(
            10,
            'Kostal',
            "Inverter '" + str(self.inverterType) + "' available @" + str(self.inverterIP)
        )

    # return the total consumption by the household
    # deduct charger load - if car(s) charging
    def getConsumption(self):
        if not self.enabled:
            self.master.debugLog(
                1,
                'Kostal,',
                'Kostal EMS Module Disabled. Can\'t provide provide consumption data!')
            return 0

        # Perform updates if necessary
        self.update()

        # return the total household consumption
        if self.home_fromGrid > 0.0 or self.home_fromSolar > 0.0:
            self.master.debugLog(
                10,
                'Kostal',
                'Total consumption from Grid: {:.2f} W'.format(self.home_fromGrid + self.home_fromSolar)
            )
            return float(self.home_fromGrid + self.home_fromSolar)

        else:
            # return zero if no consumption (unlikely though...)
            return float(0.0)

    # return the generated power by the inverter
    def getGeneration(self):
        if not self.enabled:
            self.master.debugLog(
                10,
                'Kostal',
                'Kostal EMS Module Disabled. Can\'t provide generated power data!')
            return 0

        # Perform updates if necessary
        self.update()

        # Return generation value
        return float(self.totalDCPower)

    def update(self):
        if (int(self.time.time()) - self.lastFetch) > self.cacheTime:
            # Cache has expired. Fetch values from inverter via Modbus

            # let's assume the worst...for now
            self.fetchFailed = True

            # update the values by calling the corresponding update-functions
            self.updateTotalDCPower()
            self.updateHomeFromGrid()
            self.updateHomeFromSolar()

            # close Modbus connection
            self.m_client.close()

            # if updating did not failed, it was successful
            if self.fetchFailed is not True:
                self.lastFetch = int(self.time.time())
                return True

        else:
            # no need to update the cache, indicate by returning false
            return False
