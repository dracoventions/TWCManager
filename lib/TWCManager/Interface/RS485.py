import logging
import time

logger = logging.getLogger("\U0001F50C RS485")


class RS485:
    import serial

    baud = 9600
    enabled = True
    master = None
    port = None
    ser = None
    timeLastTx = 0

    def __init__(self, master):
        self.master = master
        classname = self.__class__.__name__

        # Unload if this module is disabled or misconfigured
        if "interface" in master.config and classname in master.config["interface"]:
            self.enabled = master.config["interface"][classname].get("enabled", True)
        if not self.enabled:
            self.master.releaseModule("lib.TWCManager.Interface", classname)
            return None

        # There are two places that the baud rate for the RS485 adapter may be stored.
        # The first is the legacy configuration path, and the second is the new
        # dedicated interface configuration. We check either/both for this value
        bauda = master.config["config"].get("baud", 0)
        baudb = None
        if "interface" in master.config:
            baudb = master.config["interface"]["RS485"].get("baud", 0)
        if baudb:
            self.baud = baudb
        elif bauda:
            self.baud = bauda

        # Similarly, there are two places to check for a port defined.
        porta = master.config["config"].get("rs485adapter", "")
        portb = None
        if "interface" in master.config:
            portb = master.config["interface"]["RS485"].get("port", "")
        if portb:
            self.port = portb
        elif porta:
            self.port = porta

        self.connect()

    def connect(self):
        # Reset any Slave TWC last RX heartbeat counters in case serial reconnection has occurred
        for slaveTWC in self.master.getSlaveTWCs():
            slaveTWC.timeLastRx = time.time()

        # Connect to serial port
        self.ser = self.serial.serial_for_url(self.port, self.baud, timeout=0)

    def close(self):
        # Close the serial interface
        return self.ser.close()

    def getBufferLen(self):
        # This function returns the size of the recieve buffer.
        # This is used by read functions to determine if information is waiting
        return self.ser.inWaiting()

    def read(self, len):
        # Read the specified amount of data from the serial interface
        try:
            return self.ser.read(len)
        except serial.serialutil.SerialException as e:
            logger.log(
                logging.ERROR,
                "Error reading from serial interface: {}. Will attempt re-connect.".format(
                    e
                ),
            )
            self.connect()

    def send(self, msg):
        # Send msg on the RS485 network. We'll escape bytes with a special meaning,
        # add a CRC byte to the message end, and add a C0 byte to the start and end
        # to mark where it begins and ends.

        msg = bytearray(msg)
        checksum = 0
        for i in range(1, len(msg)):
            checksum += msg[i]

        msg.append(checksum & 0xFF)

        # Escaping special chars:
        # The protocol uses C0 to mark the start and end of the message.  If a C0
        # must appear within the message, it is 'escaped' by replacing it with
        # DB and DC bytes.
        # A DB byte in the message is escaped by replacing it with DB DD.
        #
        # User FuzzyLogic found that this method of escaping and marking the start
        # and end of messages is based on the SLIP protocol discussed here:
        #   https://en.wikipedia.org/wiki/Serial_Line_Internet_Protocol

        i = 0
        while i < len(msg):
            if msg[i] == 0xC0:
                msg[i : i + 1] = b"\xdb\xdc"
                i = i + 1
            elif msg[i] == 0xDB:
                msg[i : i + 1] = b"\xdb\xdd"
                i = i + 1
            i = i + 1

        msg = bytearray(b"\xc0" + msg + b"\xc0")
        logger.log(logging.INFO9, "Tx@: " + self.master.hex_str(msg))

        self.ser.write(msg)

        self.timeLastTx = time.time()
