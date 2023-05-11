import logging
import re
import struct
import sysv_ipc
import time
import math

logger = logging.getLogger(__name__.rsplit(".")[-1])


class WebIPCControl:
    config = None
    configConfig = None
    configIPC = None
    debugLevel = 0
    master = None
    webIPCkey = None
    webIPCqueue = None

    def __init__(self, master):
        self.config = master.config
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        self.debugLevel = self.configConfig.get("debugLevel", 0)
        self.master = master

        try:
            self.configIPC = master.config["control"]["IPC"]
        except KeyError:
            self.configIPC = {}
        self.status = self.configIPC.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if not self.status:
            self.master.releaseModule("lib.TWCManager.Control", "WebIPCControl")
            return None

        # Create an IPC (Interprocess Communication) message queue that we can
        # periodically check to respond to queries from the TWCManager web interface.
        #
        # These messages will contain commands like "start charging at 10A" or may ask
        # for information like "how many amps is the solar array putting out".
        #
        # The message queue is identified by a numeric key. This script and the web
        # interface must both use the same key. The "ftok" function facilitates creating
        # such a key based on a shared piece of information that is not likely to
        # conflict with keys chosen by any other process in the system.
        #
        # ftok reads the inode number of the file or directory pointed to by its first
        # parameter. This file or dir must already exist and the permissions on it don't
        # seem to matter. The inode of a particular file or dir is fairly unique but
        # doesn't change often so it makes a decent choice for a key.  We use the parent
        # directory of the TWCManager script.
        #
        # The second parameter to ftok is a single byte that adds some additional
        # uniqueness and lets you create multiple queues linked to the file or dir in
        # the first param. We use 'T' for Tesla.
        #
        # If you can't get this to work, you can also set key = <some arbitrary number>
        # and in the web interface, use the same arbitrary number. While that could
        # conflict with another process, it's very unlikely to.
        self.webIPCkey = sysv_ipc.ftok(
            self.config["config"]["settingsPath"], ord("T"), True
        )

        # Use the key to create a message queue with read/write access for all users.
        self.webIPCqueue = sysv_ipc.MessageQueue(
            self.webIPCkey, sysv_ipc.IPC_CREAT, 0o666
        )
        if self.webIPCqueue == None:
            logger.info(
                "ERROR: Can't create Interprocess Communication message queue to communicate with web interface."
            )

        # After the IPC message queue is created, if you type 'sudo ipcs -q' on the
        # command like, you should see something like:
        # ------ Message Queues --------
        # key        msqid      owner      perms      used-bytes   messages
        # 0x5402ed16 491520     pi         666        0            0
        #
        # If you want to get rid of all queues,
        # reboot or type 'sudo ipcrm -a msg'.
        # ones you didn't create or you may crash another process.
        # Find more details in IPC here:
        # http://www.onlamp.com/pub/a/php/2004/05/13/shared_memory.html

    def trim_pad(self, s: bytearray, makeLen):
        # Trim or pad s with zeros so that it's makeLen length.
        while len(s) < makeLen:
            s += b"\x00"

        if len(s) > makeLen:
            s = s[0:makeLen]

        return s

    def processIPC(self):
        ########################################################################
        # See if there's any message from the web interface.
        # If the message is longer than msgMaxSize, MSG_NOERROR tells it to
        # return what it can of the message and discard the rest.
        # When no message is available, IPC_NOWAIT tells msgrcv to return
        # msgResult = 0 and $! = 42 with description 'No message of desired
        # type'.
        # If there is an actual error, webMsgResult will be -1.
        # On success, webMsgResult is the length of webMsgPacked.
        try:
            webMsgRaw = self.webIPCqueue.receive(False, 2)
            if len(webMsgRaw[0]) > 0:
                webMsgType = webMsgRaw[1]
                unpacked = struct.unpack("=LH", webMsgRaw[0][0:6])
                webMsgTime = unpacked[0]
                webMsgID = unpacked[1]
                webMsg = webMsgRaw[0][6 : len(webMsgRaw[0])]

                webMsgRedacted = webMsg
                # Hide car password in web request to send password to Tesla
                m = re.search(b"^(carApiEmailPassword=[^\n]+\n)", webMsg, re.MULTILINE)
                if m:
                    webMsgRedacted = m.group(1) + b"[HIDDEN]"

                logger.info(
                    "Web query: '"
                    + str(webMsgRedacted)
                    + "', id "
                    + str(webMsgID)
                    + ", time "
                    + str(webMsgTime)
                    + ", type "
                    + str(webMsgType)
                )
                webResponseMsg = ""
                numPackets = 0
                slaveTWCRoundRobin = self.master.getSlaveTWCs()
                if webMsg == b"getStatus":
                    needCarApiBearerToken = False
                    if (
                        self.master.getModuleByName("TeslaAPI").getCarApiBearerToken()
                        == ""
                    ):
                        for i in range(0, self.master.countSlaveTWC()):
                            if slaveTWCRoundRobin[i].protocolVersion == 2:
                                needCarApiBearerToken = True

                    webResponseMsg = (
                        "%.2f" % (self.master.getMaxAmpsToDivideAmongSlaves())
                        + "`"
                        + "%.2f" % (self.config["config"]["wiringMaxAmpsAllTWCs"])
                        + "`"
                        + "%.2f" % (self.config["config"]["minAmpsPerTWC"])
                        + "`"
                        + "%.2f" % (self.master.getChargeNowAmps())
                        + "`"
                        + str(self.master.getNonScheduledAmpsMax())
                        + "`"
                        + str(self.master.getScheduledAmpsMax())
                        + "`"
                        + "%02d:%02d"
                        % (
                            int(self.master.getScheduledAmpsStartHour()),
                            int((self.master.getScheduledAmpsStartHour() % 1) * 60),
                        )
                        + "`"
                        + "%02d:%02d"
                        % (
                            int(self.master.getScheduledAmpsEndHour()),
                            int((self.master.getScheduledAmpsEndHour() % 1) * 60),
                        )
                        + "`"
                        + str(self.master.getScheduledAmpsDaysBitmap())
                        + "`"
                        + "%02d:%02d"
                        % (
                            int(self.master.getHourResumeTrackGreenEnergy()),
                            int((self.master.getHourResumeTrackGreenEnergy() % 1) * 60),
                        )
                        +
                        # Send 1 if we need an email/password entered for car api, otherwise send 0
                        "`"
                        + ("1" if needCarApiBearerToken else "0")
                        + "`"
                        + str(self.master.countSlaveTWC())
                    )

                    for i in range(0, self.master.countSlaveTWC()):
                        webResponseMsg += (
                            "`"
                            + "%02X%02X"
                            % (
                                self.master.getSlaveTWCID(i)[0],
                                self.master.getSlaveTWCID(i)[1],
                            )
                            + "~"
                            + str(slaveTWCRoundRobin[i].maxAmps)
                            + "~"
                            + "%.2f" % (slaveTWCRoundRobin[i].reportedAmpsActual)
                            + "~"
                            + str(slaveTWCRoundRobin[i].lastAmpsOffered)
                            + "~"
                            + str(slaveTWCRoundRobin[i].reportedState)
                        )

                elif webMsg[0:20] == b"setNonScheduledAmps=":
                    m = re.search(b"([-0-9]+)", webMsg[19 : len(webMsg)])
                    if m:
                        self.master.setNonScheduledAmpsMax(int(m.group(1)))

                        # Save nonScheduledAmpsMax to SD card so the setting
                        # isn't lost on power failure or script restart.
                        self.master.queue_background_task({"cmd": "saveSettings"})
                elif webMsg[0:17] == b"setScheduledAmps=":
                    m = re.search(
                        b"([-0-9]+)\nstartTime=([-0-9]+):([0-9]+)\nendTime=([-0-9]+):([0-9]+)\ndays=([0-9]+)",
                        webMsg[17 : len(webMsg)],
                        re.MULTILINE,
                    )
                    if m:
                        self.master.setScheduledAmpsMax(int(m.group(1)))
                        self.master.setScheduledAmpsStartHour(
                            int(m.group(2)) + (int(m.group(3)) / 60)
                        )
                        self.master.setScheduledAmpsEndHour(
                            int(m.group(4)) + (int(m.group(5)) / 60)
                        )
                        self.master.setScheduledAmpsDaysBitmap(int(m.group(6)))
                        self.master.queue_background_task({"cmd": "saveSettings"})
                elif webMsg[0:30] == b"setResumeTrackGreenEnergyTime=":
                    m = re.search(
                        b"([-0-9]+):([0-9]+)", webMsg[30 : len(webMsg)], re.MULTILINE
                    )
                    if m:
                        self.master.setHourResumeTrackGreenEnergy(
                            int(m.group(1)) + (int(m.group(2)) / 60)
                        )
                        self.master.queue_background_task({"cmd": "saveSettings"})
                elif webMsg[0:11] == b"sendTWCMsg=":
                    m = re.search(
                        b"([0-9a-fA-F]+)", webMsg[11 : len(webMsg)], re.MULTILINE
                    )
                    if m:
                        twcMsg = self.trim_pad(
                            bytearray.fromhex(m.group(1).decode("ascii")),
                            15
                            if self.master.countSlaveTWC() == 0
                            or slaveTWCRoundRobin[0].protocolVersion == 2
                            else 13,
                        )
                        if (twcMsg[0:2] == b"\xFC\x19") or (twcMsg[0:2] == b"\xFC\x1A"):
                            logger.info(
                                "\n*** ERROR: Web interface requested sending command:\n"
                                + self.master.hex_str(twcMsg)
                                + "\nwhich could permanently disable the TWC.  Aborting.\n"
                            )
                        elif twcMsg[0:2] == b"\xFB\xE8":
                            logger.info(
                                "\n*** ERROR: Web interface requested sending command:\n"
                                + self.master.hex_str(twcMsg)
                                + "\nwhich could crash the TWC.  Aborting.\n"
                            )
                        else:
                            self.master.lastTWCResponseMsg = bytearray()
                            self.master.getModuleByName("RS485").send(twcMsg)
                elif webMsg == b"getLastTWCMsgResponse":
                    if (
                        self.master.lastTWCResponseMsg != None
                        and self.master.lastTWCResponseMsg != b""
                    ):
                        webResponseMsg = self.master.hex_str(
                            self.master.lastTWCResponseMsg
                        )
                    else:
                        webResponseMsg = "None"
                elif webMsg[0:20] == b"carApiEmailPassword=":
                    m = re.search(
                        b"([^\n]+)\n([^\n]+)", webMsg[20 : len(webMsg)], re.MULTILINE
                    )
                    if m:
                        self.master.queue_background_task(
                            {
                                "cmd": "carApiEmailPassword",
                                "email": m.group(1).decode("ascii"),
                                "password": m.group(2).decode("ascii"),
                            }
                        )
                elif webMsg[0:23] == b"setMasterHeartbeatData=":
                    m = re.search(
                        b"([0-9a-fA-F]*)", webMsg[23 : len(webMsg)], re.MULTILINE
                    )
                    if m:
                        if len(m.group(1)) > 0:
                            overrideMasterHeartbeatData = self.trim_pad(
                                bytearray.fromhex(m.group(1).decode("ascii")),
                                9 if slaveTWCRoundRobin[0].protocolVersion == 2 else 7,
                            )
                        else:
                            overrideMasterHeartbeatData = b""
                elif webMsg == b"chargeNow":
                    self.master.setChargeNowAmps(
                        self.master.config["config"]["wiringMaxAmpsAllTWCs"]
                    )
                    self.master.setChargeNowTimeEnd(60 * 60 * 24)
                    self.master.queue_background_task({"cmd": "saveSettings"})
                elif webMsg == b"chargeNowCancel":
                    self.master.resetChargeNowAmps()
                elif webMsg == b"dumpState":
                    # dumpState commands are used for debugging. They are called
                    # using a web page:
                    # http://(Pi address)/index.php?submit=1&dumpState=1
                    carapi = self.master.getModuleByName("TeslaAPI")
                    webResponseMsg = (
                        "time="
                        + str(time.time())
                        + ", fakeMaster="
                        + str(self.config["config"]["fakeMaster"])
                        + ", rs485Adapter="
                        + str(self.config["interface"]["RS485"]["port"])
                        + ", baud="
                        + str(self.config["interface"]["RS485"]["baud"])
                        + ", wiringMaxAmpsAllTWCs="
                        + str(self.config["config"]["wiringMaxAmpsAllTWCs"])
                        + ", wiringMaxAmpsPerTWC="
                        + str(self.config["config"]["wiringMaxAmpsPerTWC"])
                        + ", minAmpsPerTWC="
                        + str(self.config["config"]["minAmpsPerTWC"])
                        + ", greenEnergyAmpsOffset="
                        + str(self.config["config"]["greenEnergyAmpsOffset"])
                        + ", debugLevel="
                        + str(self.config["config"]["debugLevel"])
                        + "\n"
                    )
                    webResponseMsg += (
                        "carApiLastStartOrStopChargeTime="
                        + str(
                            time.strftime(
                                "%m-%d-%y %H:%M:%S",
                                time.localtime(carapi.getLastStartOrStopChargeTime()),
                            )
                        )
                        + "\ncarApiLastErrorTime="
                        + str(
                            time.strftime(
                                "%m-%d-%y %H:%M:%S",
                                time.localtime(carapi.getCarApiLastErrorTime()),
                            )
                        )
                        + "\ncarApiTokenExpireTime="
                        + str(
                            time.strftime(
                                "%m-%d-%y %H:%M:%S",
                                time.localtime(carapi.getCarApiTokenExpireTime()),
                            )
                        )
                        + "\n"
                    )

                    for vehicle in carapi.getCarApiVehicles():
                        webResponseMsg += str(vehicle.__dict__) + "\n"

                    webResponseMsg += "slaveTWCRoundRobin:\n"
                    for slaveTWC in self.master.getSlaveTWCs():
                        webResponseMsg += str(slaveTWC.__dict__) + "\n"

                    numPackets = math.ceil(len(webResponseMsg) / 290)
                elif webMsg[0:14] == b"setDebugLevel=":
                    m = re.search(b"([-0-9]+)", webMsg[14 : len(webMsg)], re.MULTILINE)
                    if m:
                        self.config["config"]["debugLevel"] = int(m.group(1))
                else:
                    logger.info("Unknown IPC request from web server: " + str(webMsg))

                if len(webResponseMsg) > 0:
                    logger.log(
                        logging.INFO5, "Web query response: '" + webResponseMsg + "'"
                    )

                    try:
                        if numPackets == 0:
                            if len(webResponseMsg) > 290:
                                webResponseMsg = webResponseMsg[0:290]

                            self.webIPCqueue.send(
                                struct.pack(
                                    "=LH" + str(len(webResponseMsg)) + "s",
                                    webMsgTime,
                                    webMsgID,
                                    webResponseMsg.encode("ascii"),
                                ),
                                block=False,
                            )
                        else:
                            # In this case, block=False prevents blocking if the message
                            # queue is too full for our message to fit. Instead, an
                            # error is returned.
                            msgTemp = struct.pack(
                                "=LH1s", webMsgTime, webMsgID, bytearray([numPackets])
                            )
                            self.webIPCqueue.send(msgTemp, block=False)
                            for i in range(0, numPackets):
                                packet = webResponseMsg[i * 290 : i * 290 + 290]
                                self.webIPCqueue.send(
                                    struct.pack(
                                        "=LH" + str(len(packet)) + "s",
                                        webMsgTime,
                                        webMsgID,
                                        packet.encode("ascii"),
                                    ),
                                    block=False,
                                )

                    except sysv_ipc.BusyError:
                        logger.error(
                            "Error: IPC queue full when trying to send response to web interface."
                        )

        except sysv_ipc.BusyError:
            # No web message is waiting.
            pass
