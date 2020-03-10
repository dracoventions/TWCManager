class RS485:

  import time
  debugLevel       = 0
  master           = None
  ser              = None

  def __init__(self, master):
    self.master = master
    self.ser    = master.ser
    try:
        self.debugLevel = master.config['config']['debugLevel']
    except KeyError:
        pass

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
    while(i < len(msg)):
        if(msg[i] == 0xc0):
            msg[i:i+1] = b'\xdb\xdc'
            i = i + 1
        elif(msg[i] == 0xdb):
            msg[i:i+1] = b'\xdb\xdd'
            i = i + 1
        i = i + 1

    msg = bytearray(b'\xc0' + msg + b'\xc0')

    if(self.master.config['config']['debugLevel'] >= 9):
        print("Tx@" + self.master.time_now() + ": " + self.master.hex_str(msg))

    self.ser.write(msg)

    self.timeLastTx = self.time.time()

