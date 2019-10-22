import re
import struct
import sysv_ipc
import time

class WebIPCControl:

  carapi       = None
  config       = None
  configConfig = None
  debugLevel   = 0
  master       = None

  def __init__(self, master):
    self.carapi     = master.carapi
    self.config     = master.config
    try:
      self.configConfig = master.config['config']
    except KeyError:
      self.configConfig = {}
    self.debugLevel     = self.configConfig.get('debugLevel', 0)
    self.master         = master

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("WebIPC: (" + str(minlevel) + ") " + message)

  def processIPC(self, webIPCqueue):

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
        webMsgRaw = webIPCqueue.receive(False, 2)
        if(len(webMsgRaw[0]) > 0):
            webMsgType = webMsgRaw[1]
            unpacked = struct.unpack('=LH', webMsgRaw[0][0:6])
            webMsgTime = unpacked[0]
            webMsgID = unpacked[1]
            webMsg = webMsgRaw[0][6:len(webMsgRaw[0])]

            if(self.config['config']['debugLevel'] >= 1):
                webMsgRedacted = webMsg
                # Hide car password in web request to send password to Tesla
                m = re.search(b'^(carApiEmailPassword=[^\n]+\n)', webMsg, re.MULTILINE)
                if(m):
                    webMsgRedacted = m.group(1) + b'[HIDDEN]'
                self.debugLog(1, "Web query: '" + str(webMsgRedacted) + "', id " + str(webMsgID) +
                                   ", time " + str(webMsgTime) + ", type " + str(webMsgType))
            webResponseMsg = ''
            numPackets = 0
            slaveTWCRoundRobin = self.master.getSlaveTWCs()
            if(webMsg == b'getStatus'):
                needCarApiBearerToken = False
                if(self.carapi.getCarApiBearerToken() == ''):
                    for i in range(0, self.master.countSlaveTWC()):
                        if(slaveTWCRoundRobin[i].protocolVersion == 2):
                            needCarApiBearerToken = True

                webResponseMsg = (
                    "%.2f" % (self.master.getMaxAmpsToDivideAmongSlaves()) +
                    '`' + "%.2f" % (self.config['config']['wiringMaxAmpsAllTWCs']) +
                    '`' + "%.2f" % (self.config['config']['minAmpsPerTWC']) +
                    '`' + "%.2f" % (self.master.getChargeNowAmps()) +
                    '`' + str(self.master.getNonScheduledAmpsMax()) +
                    '`' + str(self.master.getScheduledAmpsMax()) +
                    '`' + "%02d:%02d" % (int(self.master.getScheduledAmpsStartHour()),
                                         int((self.master.getScheduledAmpsStartHour() % 1) * 60)) +
                    '`' + "%02d:%02d" % (int(self.master.getScheduledAmpsEndHour()),
                                         int((self.master.getScheduledAmpsEndHour() % 1) * 60)) +
                    '`' + str(self.master.getScheduledAmpsDaysBitmap()) +
                    '`' + "%02d:%02d" % (int(self.master.getHourResumeTrackGreenEnergy()),
                                         int((self.master.getHourResumeTrackGreenEnergy() % 1) * 60)) +
                    # Send 1 if we need an email/password entered for car api, otherwise send 0
                    '`' + ('1' if needCarApiBearerToken else '0') +
                    '`' + str(self.master.countSlaveTWC())
                    )

                for i in range(0, self.master.countSlaveTWC()):
                    webResponseMsg += (
                        '`' + "%02X%02X" % (self.master.getSlaveTWCID(i)[0],
                                            self.master.getSlaveTWCID(i)[1]) +
                        '~' + str(slaveTWCRoundRobin[i].maxAmps) +
                        '~' + "%.2f" % (slaveTWCRoundRobin[i].reportedAmpsActual) +
                        '~' + str(slaveTWCRoundRobin[i].lastAmpsOffered) +
                        '~' + str(slaveTWCRoundRobin[i].reportedState))

            elif(webMsg[0:20] == b'setNonScheduledAmps='):
                m = re.search(b'([-0-9]+)', webMsg[19:len(webMsg)])
                if(m):
                    self.master.setNonScheduledAmpsMax(int(m.group(1)))

                    # Save nonScheduledAmpsMax to SD card so the setting
                    # isn't lost on power failure or script restart.
                    self.master.saveSettings()
            elif(webMsg[0:17] == b'setScheduledAmps='):
                m = re.search(b'([-0-9]+)\nstartTime=([-0-9]+):([0-9]+)\nendTime=([-0-9]+):([0-9]+)\ndays=([0-9]+)', \
                              webMsg[17:len(webMsg)], re.MULTILINE)
                if(m):
                    self.master.setScheduledAmpsMax(int(m.group(1)))
                    self.master.setScheduledAmpsStartHour(int(m.group(2)) + (int(m.group(3)) / 60))
                    self.master.setScheduledAmpsEndHour(int(m.group(4)) + (int(m.group(5)) / 60))
                    self.master.setScheduledAmpsDaysBitmap(int(m.group(6)))
                    self.master.saveSettings()
            elif(webMsg[0:30] == b'setResumeTrackGreenEnergyTime='):
                m = re.search(b'([-0-9]+):([0-9]+)', webMsg[30:len(webMsg)], re.MULTILINE)
                if(m):
                    self.master.setHourResumeTrackGreenEnergy(int(m.group(1)) + (int(m.group(2)) / 60))
                    self.master.saveSettings()
            elif(webMsg[0:11] == b'sendTWCMsg='):
                m = re.search(b'([0-9a-fA-F]+)', webMsg[11:len(webMsg)], re.MULTILINE)
                if(m):
                    twcMsg = trim_pad(bytearray.fromhex(m.group(1).decode('ascii')), 15 if self.master.countSlaveTWC() == 0 \
                                      or slaveTWCRoundRobin[0].protocolVersion == 2 else 13)
                    if((twcMsg[0:2] == b'\xFC\x19') or (twcMsg[0:2] == b'\xFC\x1A')):
                        print("\n*** ERROR: Web interface requested sending command:\n"
                              + hex_str(twcMsg)
                              + "\nwhich could permanently disable the TWC.  Aborting.\n")
                    elif((twcMsg[0:2] == b'\xFB\xE8')):
                        print("\n*** ERROR: Web interface requested sending command:\n"
                              + hex_str(twcMsg)
                              + "\nwhich could crash the TWC.  Aborting.\n")
                    else:
                        lastTWCResponseMsg = bytearray();
                        send_msg(twcMsg)
            elif(webMsg == b'getLastTWCMsgResponse'):
                if(lastTWCResponseMsg != None and lastTWCResponseMsg != b''):
                    webResponseMsg = hex_str(lastTWCResponseMsg)
                else:
                    webResponseMsg = 'None'
            elif(webMsg[0:20] == b'carApiEmailPassword='):
                m = re.search(b'([^\n]+)\n([^\n]+)', webMsg[20:len(webMsg)], re.MULTILINE)
                if(m):
                    self.master.queue_background_task({'cmd':'carApiEmailPassword',
                                              'email':m.group(1).decode('ascii'),
                                              'password':m.group(2).decode('ascii')})
            elif(webMsg[0:23] == b'setMasterHeartbeatData='):
                m = re.search(b'([0-9a-fA-F]*)', webMsg[23:len(webMsg)], re.MULTILINE)
                if(m):
                    if(len(m.group(1)) > 0):
                        overrideMasterHeartbeatData = trim_pad(bytearray.fromhex(m.group(1).decode('ascii')),
                                                               9 if slaveTWCRoundRobin[0].protocolVersion == 2 else 7)
                    else:
                        overrideMasterHeartbeatData = b''
            elif(webMsg == b'chargeNow'):
                self.master.setChargeNowAmps(self.master.config['config']['wiringMaxAmpsAllTWCs'])
                self.master.setChargeNowTimeEnd(60*60*24)
                self.master.saveSettings()
            elif(webMsg == b'chargeNowCancel'):
                self.master.resetChargeNowAmps()
            elif(webMsg == b'dumpState'):
                # dumpState commands are used for debugging. They are called
                # using a web page:
                # http://(Pi address)/index.php?submit=1&dumpState=1
                webResponseMsg = ('time=' + str(now) + ', fakeMaster='
                    + str(self.config['config']['fakeMaster']) + ', rs485Adapter=' + self.config['config']['rs485adapter']
                    + ', baud=' + str(self.config['config']['baud'])
                    + ', wiringMaxAmpsAllTWCs=' + str(self.config['config']['wiringMaxAmpsAllTWCs'])
                    + ', wiringMaxAmpsPerTWC=' + str(self.config['config']['wiringMaxAmpsPerTWC'])
                    + ', minAmpsPerTWC=' + str(self.config['config']['minAmpsPerTWC'])
                    + ', greenEnergyAmpsOffset=' + str(self.config['config']['greenEnergyAmpsOffset'])
                    + ', debugLevel=' + str(self.config['config']['debugLevel'])
                    + '\n')
                webResponseMsg += (
                    'carApiStopAskingToStartCharging=' + str(carApiStopAskingToStartCharging)
                    + '\ncarApiLastStartOrStopChargeTime=' + str(time.strftime("%m-%d-%y %H:%M:%S", time.localtime(self.carapi.getLastStartOrStopChargeTime())))
                    + '\ncarApiLastErrorTime=' + str(time.strftime("%m-%d-%y %H:%M:%S", time.localtime(self.carapi.getCarApiLastErrorTime())))
                    + '\ncarApiTokenExpireTime=' + str(time.strftime("%m-%d-%y %H:%M:%S", time.localtime(self.carapi.getCarApiTokenExpireTime())))
                    + '\n')

                for vehicle in carapi.getCarApiVehicles():
                    webResponseMsg += str(vehicle.__dict__) + '\n'

                webResponseMsg += 'slaveTWCRoundRobin:\n'
                for slaveTWC in self.master.getSlaveTWCs():
                    webResponseMsg += str(slaveTWC.__dict__) + '\n'

                numPackets = math.ceil(len(webResponseMsg) / 290)
            elif(webMsg[0:14] == b'setDebugLevel='):
                m = re.search(b'([-0-9]+)', webMsg[14:len(webMsg)], re.MULTILINE)
                if(m):
                    self.config['config']['debugLevel'] = int(m.group(1))
            else:
                self.debugLog(1, "Unknown IPC request from web server: " + str(webMsg))

            if(len(webResponseMsg) > 0):
                self.debugLog(5, "Web query response: '" + webResponseMsg + "'")

                try:
                    if(numPackets == 0):
                        if(len(webResponseMsg) > 290):
                            webResponseMsg = webResponseMsg[0:290]

                        webIPCqueue.send(struct.pack('=LH' + str(len(webResponseMsg)) + 's', webMsgTime, webMsgID,
                               webResponseMsg.encode('ascii')), block=False)
                    else:
                        # In this case, block=False prevents blocking if the message
                        # queue is too full for our message to fit. Instead, an
                        # error is returned.
                        msgTemp = struct.pack('=LH1s', webMsgTime, webMsgID, bytearray([numPackets]))
                        webIPCqueue.send(msgTemp, block=False)
                        for i in range(0, numPackets):
                            packet = webResponseMsg[i*290:i*290+290]
                            webIPCqueue.send(struct.pack('=LH' + str(len(packet)) + 's', webMsgTime, webMsgID,
                               packet.encode('ascii')), block=False)

                except sysv_ipc.BusyError:
                    self.debugLog(0, "Error: IPC queue full when trying to send response to web interface.")

    except sysv_ipc.BusyError:
        # No web message is waiting.
        pass

