# Kostal Modbus interface for realtime solar data
# written by Andreas Hopfenblatt in Q4/2020.
# Contact: hopfi2k@me.com
# Tested with Kostal Plenticore Hybrid 10 inverter
# should work with other Kostal inverters too
# connects only via ModBus TCP to the inverter
# use on your own risk
#
# Changelog:
# 02/11/2020    Initial release
# 03/02/2021    Code refactoring and cleanup
#               Auto detect byte order (since firmware 0.1.17.05075)
#               Overall stability and performance improvements
#               Show model and serial number of Inverter in log
#
import logging
import time
from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils

MIN_CACHE_SECONDS = 10
ENDIAN_BIG = 0x01  # big endian (ABCD) Sunspec
ENDIAN_LITTLE = 0x00  # little endian (CDAB) Standard Modbus

logger = logging.getLogger(__name__.rsplit(".")[-1])


#
# Kostal Inverter Class
#
class Kostal:
    # Class attributes
    GridFrequency = 0  # address 0x98 (152)
    TotalDCPower = 0  # address 0x64 (100)
    HomeFromGrid = 0  # address 0x6c (108)
    HomeFromPV = 0  # address 0x72 (114)

    #
    # Constructor
    #
    def __init__(self, master):
        self.master = master
        self.config = master.config
        self.lastUpdate = 0

        # try to read the config file
        try:
            self.configConfig = master.config["config"]
            self.configKostal = master.config["sources"]["Kostal"]
        except KeyError:
            self.configConfig = {}
            self.configKostal = {}

        # read configuration values and initialize variables
        self.enabled = self.configKostal.get("enabled", False)
        self.host = self.configKostal.get("serverIP", None)
        self.port = int(self.configKostal.get("modbusPort", 1502))
        self.unitID = int(self.configKostal.get("unitID", 71))

        # Unload if this module is disabled or misconfigured
        if (not self.enabled) or (not self.host):
            self.master.releaseModule("lib.TWCManager.EMS", "Kostal")
            return None

        # try to open open the Modbus connection
        try:
            self.modbus = ModbusClient(
                host=self.host, port=self.port, unit_id=self.unitID, auto_open=True
            )
            if not self.modbus.open() is True:
                raise ValueError
        except ValueError:
            # if connection not possible, print error message and unload module
            logger.info(
                "ERROR connecting to inverter. Please check your configuration!"
            )
            self.master.releaseModule("lib.TWCManager.EMS", "Kostal")
        else:
            # detected byte order (Little/Big Endian) by reading register 0x05
            self.byteorder = ENDIAN_LITTLE
            if self.modbus.read_holding_registers(5, 1)[0] == ENDIAN_BIG:
                self.byteorder = ENDIAN_BIG

            # get basic inverter info and output informations into log
            inv_model = self.__readModbus(768, "String")
            inv_class = self.__readModbus(800, "String")
            inv_serial = self.__readModbus(559, "String")
            logger.info(
                inv_model + " " + inv_class + " (S/N: " + inv_serial + ") found."
            )

            # module successfully loaded update all values
            self.__update()

    #
    # Destructor
    # Makes sure that an open Modbus-Connection is gracefully closed
    #
    def __del(self):
        if self.modbus.is_open() is True:
            self.modbus.close()

    #
    # Privat Method for reading Modbus values
    # read registers directly from the inverter via Modbus protocol
    #
    def __readModbus(self, address, data_format="Float"):

        # open the Modbus connection if neccessary
        if not self.modbus.is_open():
            self.modbus.open()

        # default data length is 1 ('U16')
        length = 1

        # if we are retreiving floats, its two bytes
        if data_format == "Float":
            length = 2

        # for strings its either 8, 16 or 32 byte, depending on the register
        elif data_format == "String":
            if address in [8, 14, 38, 46, 420, 428, 436, 446, 454, 517]:
                length = 8
            elif address in [535, 559]:
                length = 16
            else:
                length = 32

        # read the raw data from the given Modbus address
        raw = self.modbus.read_holding_registers(address, length)
        if raw is None:
            return False

        # decode the raw_data
        if data_format == "U16":
            return int(raw[0])

        elif data_format == "Float":
            if self.byteorder == ENDIAN_BIG:
                return float(utils.decode_ieee((raw[0] << 16) + raw[1]))
            else:
                return float(utils.decode_ieee((raw[1] << 16) + raw[0]))

        elif data_format == "String":
            data_string = ""
            for value in raw:
                hex_value = str(hex(value)[2:])
                left = int(str(hex_value)[:2], 16)
                right = int(str(hex_value)[-2:], 16)
                data_string += chr(left) + chr(right)

            return str(data_string)

        # if all failed, return false
        return False

    #
    # Private Method
    # Update the cached values by reading them from the Modbus
    #
    def __update(self):
        if (int(time.time()) - self.lastUpdate) > MIN_CACHE_SECONDS:
            # Cache has expired. Fetch values from inverter via Modbus

            self.GridFrequency = self.__readModbus(152, "Float")
            self.TotalDCPower = self.__readModbus(100, "Float")
            self.HomeFromGrid = self.__readModbus(108, "Float")
            self.HomeFromPV = self.__readModbus(116, "Float")

            # set the lastUpdate variable to "now"
            self.lastUpdate = time.time()

    #
    # Public Method
    # Return the total consumption by the household
    # deduct charger load - if car(s) charging
    #
    def getConsumption(self):
        # update value if neccessary
        self.__update()

        # return the total household consumption
        total = self.HomeFromGrid + self.HomeFromPV
        logger.debug("Current Home consumption: {:.2f} W".format(total))
        return float(self.HomeFromGrid + self.HomeFromPV)

    #
    # Public Method
    # Return the generated power by the inverter
    #
    def getGeneration(self):
        # update value if neccessary
        self.__update()

        # return the Solar generation power
        logger.debug("Current Solar generation: {:.2f} W".format(self.TotalDCPower))
        return float(self.TotalDCPower)
