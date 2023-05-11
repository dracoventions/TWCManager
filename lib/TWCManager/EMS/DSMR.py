# Dutch SmartMeter Serial Integration (DSMR)


class DSMR:
    import time

    baudrate = 115200
    consumedW = 0
    generatedW = 0
    serial = None
    serialPort = "/dev/ttyUSB2"
    status = False
    timeout = 0
    voltage = 0

    def __init__(self, config):
        self.baudrate = config.get("baudrate", "115200")
        self.status = config.get("enabled", False)
        self.serialPort = config.get("serialPort", "/dev/ttyUSB2")

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (not self.serialPort) or (int(self.baudRate) < 1):
            self.master.releaseModule("lib.TWCManager.EMS", "Fronius")
            return None

    def main(self):
        self.serial.port = self.serialPort
        try:
            self.serial.open()
        except ValueError:
            sys.exit("Error opening serial port (%s). exiting" % self.serial.name)
