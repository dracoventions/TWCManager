import logging
import time

logger = logging.getLogger(__name__.rsplit(".")[-1])


class Dummy:
    enabled = False
    master = None
    msgBuffer = bytes()
    proto = None
    twcID = bytearray(b"\x12\x34")
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

        # Configure the module
        if "interface" in master.config:
            if master.config["interface"][classname].get("twcID", False):
                self.twcID = bytearray(
                    str(master.config["interface"][classname].get("twcID")).encode()
                )

        # Instantiate protocol module for sending/recieving TWC protocol
        self.proto = self.master.getModuleByName("TWCProtocol")

    def close(self):
        # NOOP - No need to close anything
        return 0

    def getBufferLen(self):
        # This function returns the size of the recieve buffer.
        # This is used by read functions to determine if information is waiting
        return len(self.msgBuffer)

    def send(self, msg):
        # This is the external send interface - it is called by TWCManager which expects that it is
        # talking to a live TWC. The key here is that we treat it as our reciept interface and parse
        # the message as if we are a TWC

        packet = self.proto.parseMessage(msg)
        if packet["Command"] == "MasterLinkready2":
            self.sendInternal(
                self.proto.createMessage(
                    {
                        "Command": "SlaveLinkready",
                        "SenderID": self.twcID,
                        "Sign": self.master.getSlaveSign(),
                        "Amps": bytearray(b"\x1F\x40"),
                    }
                )
            )
        elif packet["Command"] == "MasterHeartbeat":
            self.sendInternal(
                self.proto.createMessage(
                    {
                        "Command": "SlaveHeartbeat",
                        "SenderID": self.twcID,
                        "RecieverID": packet["SenderID"],
                    }
                )
            )

        logger.log(logging.INFO9, "Tx@: " + self.master.hex_str(msg))
        self.timeLastTx = time.time()
        return 0

    def read(self, len):
        # Read our buffered messages. We simulate this by making a copy of the
        # current message buffer, clearing the read message buffer bytes and then
        # returning the copied message to TWCManager. This is what it would look
        # like if we read from a serial interface
        localMsgBuffer = self.msgBuffer[:len]
        self.msgBuffer = self.msgBuffer[len:]
        return localMsgBuffer

    def sendInternal(self, msg):
        # The sendInternal function takes a message that we would like to send
        # from the dummy module to the TWCManager, adds the required checksum,
        # updates the internal message buffer with the sent message and then
        # allows this to be polled & read by TWCManager on the next loop iteration

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

        msg = bytearray(b"\xc0" + msg + b"\xc0\xfe")
        logger.log(logging.INFO9, "TxInt@: " + self.master.hex_str(msg))

        self.msgBuffer = msg
