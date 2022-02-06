from datetime import datetime
import logging
import re
import time


logger = logging.getLogger("\u26FD Slave")


class TWCSlave:

    config = None
    configConfig = None
    TWCID = None
    __lastAPIAmpsValue = 0
    __lastAPIAmpsRequest = time.time() + 30
    __lastAPIAmpsRepeat = 0
    lastVINQuery = 0
    maxAmps = None
    master = None
    vinQueryAttempt = 0

    # Protocol 2 TWCs tend to respond to commands sent using protocol 1, so
    # default to that till we know for sure we're talking to protocol 2.
    protocolVersion = 1
    minAmpsTWCSupports = 6
    masterHeartbeatData = bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00")
    timeLastRx = time.time()

    # reported* vars below are reported to us in heartbeat messages from a Slave
    # TWC.
    reportedAmpsMax = 0
    reportedAmpsActual = 0
    reportedState = 0
    reportedAmpsLast = -1

    # history* vars are used to track power usage over time
    historyAvgAmps = 0
    historyNumSamples = 0

    # reportedAmpsActual frequently changes by small amounts, like 5.14A may
    # frequently change to 5.23A and back.
    # reportedAmpsActualSignificantChangeMonitor is set to reportedAmpsActual
    # whenever reportedAmpsActual is at least 0.8A different than
    # reportedAmpsActualSignificantChangeMonitor. Whenever
    # reportedAmpsActualSignificantChangeMonitor is changed,
    # timeReportedAmpsActualChangedSignificantly is set to the time of the
    # change. The value of reportedAmpsActualSignificantChangeMonitor should not
    # be used for any other purpose. timeReportedAmpsActualChangedSignificantly
    # is used for things like preventing start and stop charge on a car more
    # than once per minute.
    reportedAmpsActualSignificantChangeMonitor = -1
    timeReportedAmpsActualChangedSignificantly = time.time()

    lastAmpsOffered = -1
    lastAmpsDesired = -1
    useFlexAmpsToStartCharge = False
    timeLastAmpsOfferedChanged = 0
    timeLastAmpsDesiredFlipped = 0
    lastHeartbeatDebugOutput = ""
    startStopDelay = 0
    timeLastHeartbeatDebugOutput = 0
    wiringMaxAmps = 0
    lifetimekWh = 0
    voltsPhaseA = 0
    voltsPhaseB = 0
    voltsPhaseC = 0
    isCharging = 0
    lastChargingStart = 0
    VINData = ["", "", ""]
    currentVIN = ""
    lastVIN = ""

    def __init__(self, TWCID, maxAmps, config, master):
        self.config = config
        self.configConfig = self.config.get("config", {})
        self.master = master
        self.TWCID = TWCID
        self.maxAmps = maxAmps

        self.wiringMaxAmps = self.configConfig.get("wiringMaxAmpsPerTWC", 6)
        self.useFlexAmpsToStartCharge = self.configConfig.get(
            "useFlexAmpsToStartCharge", False
        )
        self.startStopDelay = self.configConfig.get("startStopDelay", 60)

    def print_status(self, heartbeatData):

        try:
            debugOutput = "SHB %02X%02X: %02X %05.2f/%05.2fA %02X%02X" % (
                self.TWCID[0],
                self.TWCID[1],
                heartbeatData[0],
                (((heartbeatData[3] << 8) + heartbeatData[4]) / 100),
                (((heartbeatData[1] << 8) + heartbeatData[2]) / 100),
                heartbeatData[5],
                heartbeatData[6],
            )
            if self.protocolVersion == 2:
                debugOutput += " %02X%02X" % (heartbeatData[7], heartbeatData[8])
            debugOutput += "  M"

            if not self.config["config"]["fakeMaster"]:
                debugOutput += " %02X%02X" % (
                    self.master.getMasterTWCID()[0],
                    self.master.getMasterTWCID()[1],
                )

            debugOutput += ": %02X %05.2f/%05.2fA %02X%02X" % (
                self.masterHeartbeatData[0],
                (
                    ((self.masterHeartbeatData[3] << 8) + self.masterHeartbeatData[4])
                    / 100
                ),
                (
                    ((self.masterHeartbeatData[1] << 8) + self.masterHeartbeatData[2])
                    / 100
                ),
                self.masterHeartbeatData[5],
                self.masterHeartbeatData[6],
            )
            if self.protocolVersion == 2:
                debugOutput += " %02X%02X" % (
                    self.masterHeartbeatData[7],
                    self.masterHeartbeatData[8],
                )

            # Only output once-per-second heartbeat debug info when it's
            # different from the last output or if the only change has been amps
            # in use and it's only changed by 1.0 or less. Also output f it's
            # been 10 mins since the last output or if logLevel is higher than
            # DEBUG (value < 10)
            lastAmpsUsed = 0
            ampsUsed = 1
            debugOutputCompare = debugOutput
            m1 = re.search(r"SHB ....: .. (..\...)/", self.lastHeartbeatDebugOutput)
            if m1:
                lastAmpsUsed = float(m1.group(1))
            m2 = re.search(r"SHB ....: .. (..\...)/", debugOutput)
            if m2:
                ampsUsed = float(m2.group(1))
                if m1:
                    debugOutputCompare = (
                        debugOutputCompare[0 : m2.start(1)]
                        + self.lastHeartbeatDebugOutput[m1.start(1) : m1.end(1)]
                        + debugOutputCompare[m2.end(1) :]
                    )
            if (
                debugOutputCompare != self.lastHeartbeatDebugOutput
                or abs(ampsUsed - lastAmpsUsed) >= 1.0
                or time.time() - self.timeLastHeartbeatDebugOutput > 600
            ):
                logger.info(debugOutput)
                self.lastHeartbeatDebugOutput = debugOutput
                self.timeLastHeartbeatDebugOutput = time.time()

                logger.info(
                    "Slave power for TWCID %02X%02X, status: %s",
                    self.TWCID[0],
                    self.TWCID[1],
                    heartbeatData[0],
                    extra={
                        "logtype": "slave_power",
                        "TWCID": self.TWCID,
                        "status": heartbeatData[0],
                    },
                )

        except IndexError:
            # This happens if we try to access, say, heartbeatData[8] when
            # len(heartbeatData) < 9. This was happening due to a bug I fixed
            # but I may as well leave this here just in case.
            if len(heartbeatData) != (7 if self.protocolVersion == 1 else 9):
                logger.log(
                    1,
                    "Error in print_status displaying heartbeatData %s",
                    self.master.hex_str(heartbeatData),
                    # "based on msg",
                    # self.master.hex_str(msg),
                )
            if len(self.masterHeartbeatData) != (7 if self.protocolVersion == 1 else 9):
                logger.info(
                    "Error in print_status displaying masterHeartbeatData",
                    self.masterHeartbeatData,
                )

    def send_slave_heartbeat(self, masterID):
        # Send slave heartbeat
        #
        # Heartbeat includes data we store in slaveHeartbeatData.
        # Meaning of data:
        #
        # Byte 1 is a state code:
        #   00 Ready
        #      Car may or may not be plugged in.
        #      When car has reached its charge target, I've repeatedly seen it
        #      change from 03 to 00 the moment I wake the car using the phone app.
        #   01 Plugged in, charging
        #   02 Error
        #      This indicates an error such as not getting a heartbeat message
        #      from Master for too long.
        #   03 Plugged in, do not charge
        #      I've seen this state briefly when plug is first inserted, and
        #      I've seen this state remain indefinitely after pressing stop
        #      charge on car's screen or when the car reaches its target charge
        #      percentage. Unfortunately, this state does not reliably remain
        #      set, so I don't think it can be used to tell when a car is done
        #      charging. It may also remain indefinitely if TWCManager script is
        #      stopped for too long while car is charging even after TWCManager
        #      is restarted. In that case, car will not charge even when start
        #      charge on screen is pressed - only re-plugging in charge cable
        #      fixes it.
        #   04 Plugged in, ready to charge or charge scheduled
        #      I've seen this state even when car is set to charge at a future
        #      time via its UI. In that case, it won't accept power offered to
        #      it.
        #   05 Busy?
        #      I've only seen it hit this state for 1 second at a time and it
        #      can seemingly happen during any other state. Maybe it means wait,
        #      I'm busy? Communicating with car?
        #   08 Starting to charge?
        #      This state may remain for a few seconds while car ramps up from
        #      0A to 1.3A, then state usually changes to 01. Sometimes car skips
        #      08 and goes directly to 01.
        #      I saw 08 consistently each time I stopped fake master script with
        #      car scheduled to charge, plugged in, charge port blue. If the car
        #      is actually charging and you stop TWCManager, after 20-30 seconds
        #      the charge port turns solid red, steering wheel display says
        #      "charge cable fault", and main screen says "check charger power".
        #      When TWCManager is started, it sees this 08 status again. If we
        #      start TWCManager and send the slave a new max power value, 08
        #      becomes 00 and car starts charging again.
        #
        #   Protocol 2 adds a number of other states:
        #   06, 07, 09
        #      These are each sent as a response to Master sending the
        #      corresponding state. Ie if Master sends 06, slave responds with
        #      06. See notes in send_master_heartbeat for meaning.
        #   0A Amp adjustment period complete
        #      Master uses state 06 and 07 to raise or lower the slave by 2A
        #      temporarily.  When that temporary period is over, it changes
        #      state to 0A.
        #   0F was reported by another user but I've not seen it during testing
        #      and have no idea what it means.
        #
        # Byte 2-3 is the max current available as provided by bytes 2-3 in our
        # fake master status.
        # For example, if bytes 2-3 are 0F A0, combine them as 0x0fa0 hex which
        # is 4000 in base 10. Move the decimal point two places left and you get
        # 40.00Amps max.
        #
        # Byte 4-5 represents the power the car is actually drawing for
        # charging. When a car is told to charge at 19A you may see a value like
        # 07 28 which is 0x728 hex or 1832 in base 10. Move the decimal point
        # two places left and you see the charger is using 18.32A.
        # Some TWCs report 0A when a car is not charging while others may report
        # small values such as 0.25A. I suspect 0A is what should be reported
        # and any small value indicates a minor calibration error.
        #
        # Remaining bytes are always 00 00 from what I've seen and could be
        # reserved for future use or may be used in a situation I've not
        # observed.  Protocol 1 uses two zero bytes while protocol 2 uses four.

        ###############################
        # How was the above determined?
        #
        # An unplugged slave sends a status like this:
        #   00 00 00 00 19 00 00
        #
        # A real master always sends all 00 status data to a slave reporting the
        # above status. slaveHeartbeatData[0] is the main driver of how master
        # responds, but whether slaveHeartbeatData[1] and [2] have 00 or non-00
        # values also matters.
        #
        # I did a test with a protocol 1 TWC with fake slave sending
        # slaveHeartbeatData[0] values from 00 to ff along with
        # slaveHeartbeatData[1-2] of 00 and whatever
        # value Master last responded with. I found:
        #   Slave sends:     04 00 00 00 19 00 00
        #   Master responds: 05 12 c0 00 00 00 00
        #
        #   Slave sends:     04 12 c0 00 19 00 00
        #   Master responds: 00 00 00 00 00 00 00
        #
        #   Slave sends:     08 00 00 00 19 00 00
        #   Master responds: 08 12 c0 00 00 00 00
        #
        #   Slave sends:     08 12 c0 00 19 00 00
        #   Master responds: 00 00 00 00 00 00 00
        #
        # In other words, master always sends all 00 unless slave sends
        # slaveHeartbeatData[0] 04 or 08 with slaveHeartbeatData[1-2] both 00.
        #
        # I interpret all this to mean that when slave sends
        # slaveHeartbeatData[1-2] both 00, it's requesting a max power from
        # master. Master responds by telling the slave how much power it can
        # use. Once the slave is saying how much max power it's going to use
        # (slaveHeartbeatData[1-2] = 12 c0 = 32.00A), master indicates that's
        # fine by sending 00 00.
        #
        # However, if the master wants to set a lower limit on the slave, all it
        # has to do is send any heartbeatData[1-2] value greater than 00 00 at
        # any time and slave will respond by setting its
        # slaveHeartbeatData[1-2] to the same value.
        #
        # I thought slave might be able to negotiate a lower value if, say, the
        # car reported 40A was its max capability or if the slave itself could
        # only handle 80A, but the slave dutifully responds with the same value
        # master sends it even if that value is an insane 655.35A. I tested
        # these values on car which has a 40A limit when AC charging and
        # slave accepts them all:
        #   0f aa (40.10A)
        #   1f 40 (80.00A)
        #   1f 41 (80.01A)
        #   ff ff (655.35A)

        if self.protocolVersion == 1 and len(self.master.slaveHeartbeatData) > 7:
            # Cut array down to length 7
            self.master.slaveHeartbeatData = self.master.slaveHeartbeatData[0:7]
        elif self.protocolVersion == 2:
            while len(self.master.slaveHeartbeatData) < 9:
                # Increase array length to 9
                self.master.slaveHeartbeatData.append(0x00)

        self.master.getModulesByType("Interface")[0]["ref"].send(
            bytearray(b"\xFD\xE0")
            + self.master.getFakeTWCID()
            + bytearray(masterID)
            + bytearray(self.master.slaveHeartbeatData)
        )

    def send_master_heartbeat(self):
        # Send our fake master's heartbeat to this TWCSlave.
        #
        # Heartbeat includes 7 bytes (Protocol 1) or 9 bytes (Protocol 2) of data
        # that we store in masterHeartbeatData.

        if self.master.settings.get("respondToSlaves", 1) == 0:
            if (
                self.master.settings.get("respondToSlavesExpiry", time.time())
                > time.time()
            ):
                # We have been instructed not to send master heartbeats
                return
            else:
                # We were previously told to stop responding to slaves, but
                # the time limit for this has been exceeded. Start responding
                # again
                self.master.settings["respondToSlaves"] = 1

        # Meaning of data:
        #
        # Byte 1 is a command:
        #   00 Make no changes
        #   02 Error
        #     Byte 2 appears to act as a bitmap where each set bit causes the
        #     slave TWC to enter a different error state. First 8 digits below
        #     show which bits are set and these values were tested on a Protocol
        #     2 TWC:
        #       0000 0001 = Middle LED blinks 3 times red, top LED solid green.
        #                   Manual says this code means 'Incorrect rotary switch
        #                   setting.'
        #       0000 0010 = Middle LED blinks 5 times red, top LED solid green.
        #                   Manual says this code means 'More than three Wall
        #                   Connectors are set to Slave.'
        #       0000 0100 = Middle LED blinks 6 times red, top LED solid green.
        #                   Manual says this code means 'The networked Wall
        #                   Connectors have different maximum current
        #                   capabilities.'
        #   	0000 1000 = No effect
        #   	0001 0000 = No effect
        #   	0010 0000 = No effect
        #   	0100 0000 = No effect
        #       1000 0000 = No effect
        #     When two bits are set, the lowest bit (rightmost bit) seems to
        #     take precedence (ie 111 results in 3 blinks, 110 results in 5
        #     blinks).
        #
        #     If you send 02 to a slave TWC with an error code that triggers
        #     the middle LED to blink red, slave responds with 02 in its
        #     heartbeat, then stops sending heartbeat and refuses further
        #     communication. Slave's error state can be cleared by holding red
        #     reset button on its left side for about 4 seconds.
        #     If you send an error code with bitmap 11110xxx (where x is any bit),
        #     the error can not be cleared with a 4-second reset.  Instead, you
        #     must power cycle the TWC or 'reboot' reset which means holding
        #     reset for about 6 seconds till all the LEDs turn green.
        #   05 Tell slave charger to limit power to number of amps in bytes 2-3.
        #
        # Protocol 2 adds a few more command codes:
        #   06 Increase charge current by 2 amps.  Slave changes its heartbeat
        #      state to 06 in response. After 44 seconds, slave state changes to
        #      0A but amp value doesn't change.  This state seems to be used to
        #      safely creep up the amp value of a slave when the Master has extra
        #      power to distribute.  If a slave is attached to a car that doesn't
        #      want that many amps, Master will see the car isn't accepting the
        #      amps and stop offering more.  It's possible the 0A state change
        #      is not time based but rather indicates something like the car is
        #      now using as many amps as it's going to use.
        #   07 Lower charge current by 2 amps. Slave changes its heartbeat state
        #      to 07 in response. After 10 seconds, slave raises its amp setting
        #      back up by 2A and changes state to 0A.
        #      I could be wrong, but when a real car doesn't want the higher amp
        #      value, I think the TWC doesn't raise by 2A after 10 seconds. Real
        #      Master TWCs seem to send 07 state to all children periodically as
        #      if to check if they're willing to accept lower amp values. If
        #      they do, Master assigns those amps to a different slave using the
        #      06 state.
        #   08 Master acknowledges that slave stopped charging (I think), but
        #      the next two bytes contain an amp value the slave could be using.
        #   09 Tell slave charger to limit power to number of amps in bytes 2-3.
        #      This command replaces the 05 command in Protocol 1. However, 05
        #      continues to be used, but only to set an amp value to be used
        #      before a car starts charging. If 05 is sent after a car is
        #      already charging, it is ignored.
        #
        # Byte 2-3 is the max current a slave TWC can charge at in command codes
        # 05, 08, and 09. In command code 02, byte 2 is a bitmap. With other
        # command codes, bytes 2-3 are ignored.
        # If bytes 2-3 are an amp value of 0F A0, combine them as 0x0fa0 hex
        # which is 4000 in base 10. Move the decimal point two places left and
        # you get 40.00Amps max.
        #
        # Byte 4: 01 when a Master TWC is physically plugged in to a car.
        # Otherwise 00.
        #
        # Remaining bytes are always 00.
        #
        # Example 7-byte data that real masters have sent in Protocol 1:
        #   00 00 00 00 00 00 00  (Idle)
        #   02 04 00 00 00 00 00  (Error bitmap 04.  This happened when I
        #                         advertised a fake Master using an invalid max
        #                         amp value)
        #   05 0f a0 00 00 00 00  (Master telling slave to limit power to 0f a0
        #                         (40.00A))
        #   05 07 d0 01 00 00 00  (Master plugged in to a car and presumably
        #                          telling slaves to limit power to 07 d0
        #                          (20.00A). 01 byte indicates Master is plugged
        #                          in to a car.)

        if len(self.master.getMasterHeartbeatOverride()) >= 7:
            self.masterHeartbeatData = self.master.getMasterHeartbeatOverride()

        if self.protocolVersion == 2:
            # TODO: Start and stop charging using protocol 2 commands to TWC
            # instead of car api if I ever figure out how.
            if self.lastAmpsOffered == 0 and self.reportedAmpsActual > 4.0:
                now = time.time()

                if (
                    now - self.timeLastAmpsOfferedChanged < 60
                    or now - self.timeReportedAmpsActualChangedSignificantly
                    < self.startStopDelay
                    or self.reportedAmpsActual < 4.0
                ):
                    # We want to tell the car to stop charging. However, it's
                    # been less than a minute since we told it to charge or
                    # since the last significant change in the car's actual
                    # power draw or the car has not yet started to draw at least
                    # 5 amps (telling it 5A makes it actually draw around
                    # 4.18-4.27A so we check for self.reportedAmpsActual < 4.0).
                    #
                    # Once we tell the car to charge, we want to keep it going
                    # for at least a minute before turning it off again. Concern
                    # is that yanking the power at just the wrong time during
                    # the start-charge negotiation could put the car into an
                    # error state where it won't charge again without being
                    # re-plugged. This concern is hypothetical and most likely
                    # could not happen to a real car, but I'd rather not take
                    # any chances with getting someone's car into a non-charging
                    # state so they're stranded when they need to get somewhere.
                    # Note that non-Tesla cars using third-party adapters to
                    # plug in are at a higher risk of encountering this sort of
                    # hypothetical problem.
                    #
                    # The other reason for this tactic is that in the minute we
                    # wait, desiredAmpsOffered might rise above 5A in which case
                    # we won't have to turn off the charger power at all.
                    # Avoiding too many on/off cycles preserves the life of the
                    # TWC's main power relay and may also prevent errors in the
                    # car that might be caused by turning its charging on and
                    # off too rapidly.
                    #
                    # Seeing self.reportedAmpsActual < 4.0 means the car hasn't
                    # ramped up to whatever level we told it to charge at last
                    # time. It may be asleep and take up to 15 minutes to wake
                    # up, see there's power, and start charging.
                    #
                    # Unfortunately, self.reportedAmpsActual < 4.0 can also mean
                    # the car is at its target charge level and may not accept
                    # power for days until the battery drops below a certain
                    # level. I can't think of a reliable way to detect this
                    # case. When the car stops itself from charging, we'll see
                    # self.reportedAmpsActual drop to near 0.0A and
                    # heartbeatData[0] becomes 03, but we can see the same 03
                    # state when we tell the TWC to stop charging. We could
                    # record the time the car stopped taking power and assume it
                    # won't want more for some period of time, but we can't
                    # reliably detect if someone unplugged the car, drove it,
                    # and re-plugged it so it now needs power, or if someone
                    # plugged in a different car that needs power. Even if I see
                    # the car hasn't taken the power we've offered for the last
                    # hour, it's conceivable the car will reach a battery state
                    # where it decides it wants power the moment we decide it's
                    # safe to stop offering it. Thus, I think it's safest to
                    # always wait until the car has taken 5A for a minute before
                    # cutting power even if that means the car will charge for a
                    # minute when you first plug it in after a trip even at a
                    # time when no power should be available.
                    #
                    # One advantage of the above situation is that whenever you
                    # plug the car in, unless no power has been available since
                    # you unplugged, the charge port will turn green and start
                    # charging for a minute. This lets the owner quickly see
                    # that TWCManager is working properly each time they return
                    # home and plug in.
                    logger.debug(
                        "Don't stop charging TWC: "
                        + self.master.hex_str(self.TWCID)
                        + " yet because: "
                        + "time - self.timeLastAmpsOfferedChanged "
                        + str(int(now - self.timeLastAmpsOfferedChanged))
                        + " < 60 or time - self.timeReportedAmpsActualChangedSignificantly "
                        + str(
                            int(now - self.timeReportedAmpsActualChangedSignificantly)
                        )
                        + " < 60 or self.reportedAmpsActual "
                        + str(self.reportedAmpsActual)
                        + " < 4"
                    )
                    self.master.cancelStopCarsCharging()
                else:
                    # Car is trying to charge, so stop it via car API.
                    # car_api_charge() will prevent telling the car to start or stop
                    # more than once per minute. Once the car gets the message to
                    # stop, reportedAmpsActualSignificantChangeMonitor should drop
                    # to near zero within a few seconds.
                    self.master.stopCarsCharging()
            elif (
                self.lastAmpsOffered >= self.config["config"]["minAmpsPerTWC"]
                and self.reportedAmpsActual < 2.0
                and self.reportedState != 0x02
            ):
                # Car is not charging and is not reporting an error state, so
                # try starting charge via car api.
                self.master.startCarsCharging()
            elif self.reportedAmpsActual > 4.0:
                # At least one plugged in car is successfully charging. We don't
                # know which car it is, so we must set
                # vehicle.stopAskingToStartCharging = False on all vehicles such
                # that if any vehicle is not charging without us calling
                # car_api_charge(False), we'll try to start it charging again at
                # least once. This probably isn't necessary but might prevent
                # some unexpected case from never starting a charge. It also
                # seems less confusing to see in the output that we always try
                # to start API charging after the car stops taking a charge.
                for vehicle in self.master.getModuleByName(
                    "TeslaAPI"
                ).getCarApiVehicles():
                    vehicle.stopAskingToStartCharging = False

        self.master.getModulesByType("Interface")[0]["ref"].send(
            bytearray(b"\xFB\xE0")
            + self.master.getFakeTWCID()
            + bytearray(self.TWCID)
            + bytearray(self.masterHeartbeatData)
        )

    def receive_slave_heartbeat(self, heartbeatData):
        # Handle heartbeat message received from real slave TWC.

        self.master.queue_background_task({"cmd": "getLifetimekWh"})

        now = time.time()
        self.timeLastRx = now

        self.reportedAmpsMax = ((heartbeatData[1] << 8) + heartbeatData[2]) / 100
        self.reportedAmpsActual = ((heartbeatData[3] << 8) + heartbeatData[4]) / 100
        self.reportedState = heartbeatData[0]

        if self.reportedAmpsActual != self.reportedAmpsLast:
            self.reportedAmpsLast = self.reportedAmpsActual
            for module in self.master.getModulesByType("Status"):
                module["ref"].setStatus(
                    self.TWCID, "amps_in_use", "ampsInUse", self.reportedAmpsActual, "A"
                )
            self.refreshingChargerLoadStatus()
            self.master.refreshingTotalAmpsInUseStatus()

        for module in self.master.getModulesByType("Status"):
            module["ref"].setStatus(
                self.TWCID, "amps_max", "ampsMax", self.reportedAmpsMax, "A"
            )
            module["ref"].setStatus(
                self.TWCID, "state", "state", self.reportedState, ""
            )

        # Log current history
        self.historyAvgAmps = (
            (self.historyAvgAmps * self.historyNumSamples) + self.reportedAmpsActual
        ) / (self.historyNumSamples + 1)
        self.historyNumSamples += 1
        self.master.queue_background_task({"cmd": "snapHistoryData"})

        # self.lastAmpsOffered is initialized to -1.
        # If we find it at that value, set it to the current value reported by the
        # TWC.
        if self.lastAmpsOffered < 0:
            self.lastAmpsOffered = self.reportedAmpsMax

        # If power starts flowing, check whether a car has arrived
        if (
            self.reportedAmpsActualSignificantChangeMonitor < 3
            and self.reportedAmpsActual > 3
        ):
            self.master.getModuleByName("Policy").fireWebhook("start")
            self.master.queue_background_task({"cmd": "checkArrival"})

        # If power drops off, check whether a car leaves in the next little while
        if (
            self.reportedAmpsActualSignificantChangeMonitor > 2
            and self.reportedAmpsActual < 2
        ):
            self.master.getModuleByName("Policy").fireWebhook("stop")
            self.master.queue_background_task({"cmd": "checkDeparture"}, 5 * 60)
            self.master.queue_background_task({"cmd": "checkDeparture"}, 20 * 60)
            self.master.queue_background_task({"cmd": "checkDeparture"}, 45 * 60)

        # Keep track of the amps the slave is actually using and the last time it
        # changed by more than 0.8A.
        # Also update self.reportedAmpsActualSignificantChangeMonitor if it's
        # still set to its initial value of -1.
        if (
            self.reportedAmpsActualSignificantChangeMonitor < 0
            or abs(
                self.reportedAmpsActual
                - self.reportedAmpsActualSignificantChangeMonitor
            )
            > 0.8
        ):
            self.timeReportedAmpsActualChangedSignificantly = now
            self.reportedAmpsActualSignificantChangeMonitor = self.reportedAmpsActual
            for module in self.master.getModulesByType("Status"):
                module["ref"].setStatus(
                    self.TWCID, "power", "power", self.reportedAmpsActual, "A"
                )

        ltNow = time.localtime()
        hourNow = ltNow.tm_hour + (ltNow.tm_min / 60)
        yesterday = ltNow.tm_wday - 1
        if yesterday < 0:
            yesterday += 7

        # Determine our charging policy. This is the policy engine of the
        # TWCManager application. Using defined rules, we can determine how
        # we charge.
        self.master.getModuleByName("Policy").setChargingPerPolicy()

        # Determine how many cars are charging and how many amps they're using
        numCarsCharging = self.master.num_cars_charging_now()
        desiredAmpsOffered = self.master.getMaxAmpsToDivideAmongSlaves()
        flex = self.master.getAllowedFlex()

        if numCarsCharging > 0:
            desiredAmpsOffered -= sum(
                slaveTWC.reportedAmpsActual
                for slaveTWC in self.master.getSlaveTWCs()
                if slaveTWC.TWCID != self.TWCID
            )
            flex = self.master.getAllowedFlex() / numCarsCharging

            # Allocate this slave a fraction of maxAmpsToDivideAmongSlaves divided
            # by the number of cars actually charging.
            fairShareAmps = int(
                self.master.getMaxAmpsToDivideAmongSlaves() / numCarsCharging
            )
            if desiredAmpsOffered > fairShareAmps:
                desiredAmpsOffered = fairShareAmps

            logger.debug(
                "desiredAmpsOffered TWC: "
                + self.master.hex_str(self.TWCID)
                + " reduced from "
                + str(self.master.getMaxAmpsToDivideAmongSlaves())
                + " to "
                + str(desiredAmpsOffered)
                + " with "
                + str(numCarsCharging)
                + " cars charging and flex Amps of "
                + str(flex)
                + "."
            )

        minAmpsToOffer = self.config["config"]["minAmpsPerTWC"]
        if self.minAmpsTWCSupports > minAmpsToOffer:
            minAmpsToOffer = self.minAmpsTWCSupports

        if (
            desiredAmpsOffered < minAmpsToOffer
            and desiredAmpsOffered + flex >= minAmpsToOffer
            and (self.useFlexAmpsToStartCharge or self.reportedAmpsActual >= 1.0)
        ):
            desiredAmpsOffered = minAmpsToOffer

        dampenChanges = False
        if self.master.getModuleByName("Policy").policyIsGreen():
            if (now - self.timeLastAmpsDesiredFlipped) < self.startStopDelay:
                dampenChanges = True
        else:
            self.timeLastAmpsDesiredFlipped = 0

        if desiredAmpsOffered < minAmpsToOffer:
            logger.debug(
                "desiredAmpsOffered: "
                + str(desiredAmpsOffered)
                + " < minAmpsToOffer: "
                + str(minAmpsToOffer)
                + " (flexAmps: "
                + str(flex)
                + ")"
            )
            if numCarsCharging > 0:
                if (
                    self.master.getMaxAmpsToDivideAmongSlaves() / numCarsCharging
                    > minAmpsToOffer
                ):
                    # There is enough power available to give each car
                    # minAmpsToOffer, but currently-charging cars are leaving us
                    # less power than minAmpsToOffer to give this car.
                    #
                    # minAmpsToOffer is based on minAmpsPerTWC which is
                    # user-configurable, whereas self.minAmpsTWCSupports is based on
                    # the minimum amps TWC must be set to reliably start a car
                    # charging.
                    #
                    # Unfortunately, we can't tell if a car is plugged in or wanting
                    # to charge without offering it minAmpsTWCSupports. As the car
                    # gradually starts to charge, we will see it using power and
                    # tell other TWCs on the network to use less power. This could
                    # cause the sum of power used by all TWCs to exceed
                    # wiringMaxAmpsAllTWCs for a few seconds, but I don't think
                    # exceeding by up to minAmpsTWCSupports for such a short period
                    # of time will cause problems.
                    logger.debug(
                        "desiredAmpsOffered TWC: "
                        + self.master.hex_str(self.TWCID)
                        + " increased from "
                        + str(desiredAmpsOffered)
                        + " to "
                        + str(self.minAmpsTWCSupports)
                        + " (self.minAmpsTWCSupports)"
                    )

                    desiredAmpsOffered = self.minAmpsTWCSupports

                else:
                    # There is not enough power available to give each car
                    # minAmpsToOffer, so don't offer power to any cars. Alternately,
                    # we could charge one car at a time and switch cars
                    # periodically, but I'm not going to try to implement that.
                    #
                    # Note that 5A is the lowest value you can set using the Tesla car's
                    # main screen, so lower values might have some adverse affect on the
                    # car. I actually tried lower values when the sun was providing
                    # under 5A of power and found the car would occasionally set itself
                    # to state 03 and refuse to charge until you re-plugged the charger
                    # cable. Clicking "Start charging" in the car's UI or in the phone
                    # app would not start charging.
                    #
                    # A 5A charge only delivers ~3 miles of range to the car per hour,
                    # but it forces the car to remain "on" at a level that it wastes
                    # some power while it's charging. The lower the amps, the more power
                    # is wasted. This is another reason not to go below 5A.
                    #
                    # So if there isn't at least 5A of power available, pass 0A as the
                    # desired value. This tells the car to stop charging and it will
                    # enter state 03 and go to sleep. You will hear the power relay in
                    # the TWC turn off. When desiredAmpsOffered trends above 6A again,
                    # it tells the car there's power.
                    # If a car is set to energy saver mode in the car's UI, the car
                    # seems to wake every 15 mins or so (unlocking or using phone app
                    # also wakes it) and next time it wakes, it will see there's power
                    # and start charging. Without energy saver mode, the car should
                    # begin charging within about 10 seconds of changing this value.
                    logger.debug(
                        "desiredAmpsOffered TWC: "
                        + self.master.hex_str(self.TWCID)
                        + " reduced to 0 from "
                        + str(desiredAmpsOffered)
                        + " because maxAmpsToDivideAmongSlaves "
                        + str(self.master.getMaxAmpsToDivideAmongSlaves())
                        + " / numCarsCharging "
                        + str(numCarsCharging)
                        + " < minAmpsToOffer "
                        + str(minAmpsToOffer)
                    )
                    desiredAmpsOffered = 0

            else:
                # no cars are charging, and desiredAmpsOffered < minAmpsToOffer
                # so we need to set desiredAmpsOffered to 0
                logger.debug("no cars charging, setting desiredAmpsOffered to 0")
                desiredAmpsOffered = 0
        elif int(self.master.settings.get("chargeRateControl", 1)) == 2:
            # Exclusive control is given to the Tesla API to control Charge Rate
            # We offer the maximum wiring amps from the TWC, and ask the API to control charge rate

            # Call the Tesla API to set the charge rate for vehicle connected to this TWC
            # TODO: Identify vehicle
            if (
                int(desiredAmpsOffered) == self.__lastAPIAmpsValue
                and (
                    self.__lastAPIAmpsRepeat > 50 or self.__lastAPIAmpsRepeat % 10 != 0
                )
            ) or self.__lastAPIAmpsRequest > time.time() - 15:
                # Unfortunately some API requests just don't result in the desired amperage being set, so we allow one in 10
                # to be repeated up to 50, as long as none had been sent in the last 15 seconds
                # This results in a small number of repeat requests sent to the API each time
                # we change the target charge rate, but adds stability to the process
                self.__lastAPIAmpsRepeat += 1
            else:
                self.__lastAPIAmpsRequest = time.time()
                self.__lastAPIAmpsRepeat = 0
                self.__lastAPIAmpsValue = int(desiredAmpsOffered)

                # Determine vehicle to control
                targetVehicle = (
                    None if self.getLastVehicle() is None else self.getLastVehicle()
                )

                self.master.getModuleByName("TeslaAPI").setChargeRate(
                    int(desiredAmpsOffered), targetVehicle
                )

            desiredAmpsOffered = int(self.configConfig.get("wiringMaxAmpsPerTWC", 6))

        else:
            # We can tell the TWC how much power to use in 0.01A increments, but
            # the car will only alter its power in larger increments (somewhere
            # between 0.5 and 0.6A). The car seems to prefer being sent whole
            # amps and when asked to adjust between certain values like 12.6A
            # one second and 12.0A the next second, the car reduces its power
            # use to ~5.14-5.23A and refuses to go higher. So it seems best to
            # stick with whole amps.
            desiredAmpsOffered = int(desiredAmpsOffered)

            # Mid Oct 2017, Tesla pushed a firmware update to their cars
            # that seems to create the following bug:
            # If you raise desiredAmpsOffered AT ALL from the car's current
            # max amp limit, the car will drop its max amp limit to the 6A
            # setting (5.14-5.23A actual use as reported in
            # heartbeatData[2-3]). The odd fix to this problem is to tell
            # the car to raise to at least spikeAmpsToCancel6ALimit for 5 or
            # more seconds, then tell it to lower the limit to
            # desiredAmpsOffered. Even 0.01A less than
            # spikeAmpsToCancel6ALimit is not enough to cancel the 6A limit.
            #
            # I'm not sure how long we have to hold spikeAmpsToCancel6ALimit
            # but 3 seconds is definitely not enough but 5 seconds seems to
            # work. It doesn't seem to matter if the car actually hits
            # spikeAmpsToCancel6ALimit of power draw. In fact, the car is
            # slow enough to respond that even with 10s at 21A the most I've
            # seen it actually draw starting at 6A is 13A.
            logger.debug(
                "TWCID="
                + self.master.hex_str(self.TWCID)
                + " desiredAmpsOffered="
                + str(desiredAmpsOffered)
                + " spikeAmpsToCancel6ALimit="
                + str(self.master.getSpikeAmps())
                + " self.lastAmpsOffered="
                + str(self.lastAmpsOffered)
                + " self.reportedAmpsActual="
                + str(self.reportedAmpsActual)
                + " now - self.timeReportedAmpsActualChangedSignificantly="
                + str(int(now - self.timeReportedAmpsActualChangedSignificantly))
            )

            if (
                # If we just moved from a lower amp limit to
                # a higher one less than spikeAmpsToCancel6ALimit.
                (
                    desiredAmpsOffered < self.master.getSpikeAmps()
                    and desiredAmpsOffered > self.reportedAmpsMax
                    and self.master.settings.get("spikeAmpsProactively", 1)
                )
                or (
                    # ...or if we've been offering the car more amps than it's
                    # been using for at least 10 seconds, then we'll change the
                    # amps we're offering it. For some reason, the change in
                    # amps offered will get the car to up its amp draw.
                    #
                    # First, check that the car is drawing enough amps to be
                    # charging...
                    self.reportedAmpsActual > 2.0
                    and
                    # ...and car is charging at under spikeAmpsToCancel6ALimit.
                    # I think I've seen cars get stuck between spikeAmpsToCancel6ALimit
                    # and lastAmpsOffered, but more often a car will be limited
                    # to under lastAmpsOffered by its UI setting or by the
                    # charger hardware it has on board, and we don't want to
                    # keep reducing it to spikeAmpsToCancel6ALimit.
                    # If cars really are getting stuck above
                    # spikeAmpsToCancel6ALimit, I may need to implement a
                    # counter that tries spikeAmpsToCancel6ALimit only a
                    # certain number of times per hour.
                    (self.reportedAmpsActual <= self.master.getSpikeAmps())
                    and
                    # ...and car is charging at over two amps under what we
                    # want it to charge at. I have to use 2 amps because when
                    # offered, say 40A, the car charges at ~38.76A actual.
                    # Using a percentage instead of 2.0A doesn't work because
                    # 38.58/40 = 95.4% but 5.14/6 = 85.6%
                    (self.lastAmpsOffered - self.reportedAmpsActual) > 2.0
                    and
                    # ...and car hasn't changed its amp draw significantly in
                    # over 10 seconds, meaning it's stuck at its current amp
                    # draw.
                    now - self.timeReportedAmpsActualChangedSignificantly > 10
                    and self.master.settings.get("spikeAmpsReactively", 1)
                )
            ):
                # We must set desiredAmpsOffered to a value that gets
                # reportedAmpsActual (amps the car is actually using) up to
                # a value near lastAmpsOffered. At the end of all these
                # checks, we'll set lastAmpsOffered = desiredAmpsOffered and
                # timeLastAmpsOfferedChanged if the value of lastAmpsOffered was
                # actually changed.
                if (
                    self.lastAmpsOffered == self.master.getSpikeAmps()
                    and now - self.timeLastAmpsOfferedChanged > 10
                ):
                    # We've been offering the car spikeAmpsToCancel6ALimit
                    # for over 10 seconds but it's still drawing at least
                    # 2A less than spikeAmpsToCancel6ALimit.  I saw this
                    # happen once when an error stopped the car from
                    # charging and when the error cleared, it was offered
                    # spikeAmpsToCancel6ALimit as the first value it saw.
                    # The car limited itself to 6A indefinitely. In this
                    # case, the fix is to offer it lower amps.
                    logger.info(
                        "Car stuck when offered spikeAmpsToCancel6ALimit.  Offering 2 less."
                    )
                    desiredAmpsOffered = self.master.getSpikeAmps() - 2.0
                elif now - self.timeLastAmpsOfferedChanged > 5:
                    # self.lastAmpsOffered hasn't gotten the car to draw
                    # enough amps for over 5 seconds, so try
                    # spikeAmpsToCancel6ALimit
                    desiredAmpsOffered = self.master.getSpikeAmps()
                else:
                    # Otherwise, don't change the value of lastAmpsOffered.
                    desiredAmpsOffered = self.lastAmpsOffered

                # Note that the car should have no problem increasing max
                # amps to any whole value over spikeAmpsToCancel6ALimit as
                # long as it's below any upper limit manually set in the
                # car's UI. One time when I couldn't get TWC to push the car
                # over 21A, I found the car's UI had set itself to 21A
                # despite setting it to 40A the day before. I have been
                # unable to reproduce whatever caused that problem.
            elif desiredAmpsOffered < self.lastAmpsOffered:
                # Tesla doesn't mind if we set a lower amp limit than the
                # one we're currently using, but make sure we don't change
                # limits more often than every 5 seconds. This has the side
                # effect of holding spikeAmpsToCancel6ALimit set earlier for
                # 5 seconds to make sure the car sees it.
                logger.debug(
                    "Reduce amps: time - self.timeLastAmpsOfferedChanged "
                    + str(int(now - self.timeLastAmpsOfferedChanged))
                )
                if now - self.timeLastAmpsOfferedChanged < 5:
                    desiredAmpsOffered = self.lastAmpsOffered

        if (self.lastAmpsDesired <= 0 and desiredAmpsOffered > 0) or (
            self.lastAmpsDesired > 0 and desiredAmpsOffered == 0
        ):
            self.lastAmpsDesired = desiredAmpsOffered
            self.timeLastAmpsDesiredFlipped = now
            logger.debug("lastAmpsDesired flipped - now " + str(desiredAmpsOffered))

        # Keep charger on if dampening changes. See reasoning above where
        # I don't turn the charger off till it's been on for a bit.
        if dampenChanges and self.reportedAmpsActual > 0:
            desiredAmpsOffered = max(self.minAmpsTWCSupports, desiredAmpsOffered)

        # set_last_amps_offered does some final checks to see if the new
        # desiredAmpsOffered is safe. It should be called after we've picked a
        # final value for desiredAmpsOffered.
        desiredAmpsOffered = self.set_last_amps_offered(desiredAmpsOffered)

        if desiredAmpsOffered > 0:
            self.master.cancelStopCarsCharging()

        # See notes in send_slave_heartbeat() for details on how we transmit
        # desiredAmpsOffered and the meaning of the code in
        # self.masterHeartbeatData[0].
        #
        # Rather than only sending desiredAmpsOffered when slave is sending code
        # 04 or 08, it seems to work better to send desiredAmpsOffered whenever
        # it does not equal self.reportedAmpsMax reported by the slave TWC.
        # Doing it that way will get a slave charging again even when it's in
        # state 00 or 03 which it swings between after you set
        # desiredAmpsOffered = 0 to stop charging.
        #
        # I later found that a slave may end up swinging between state 01 and 03
        # when desiredAmpsOffered == 0:
        #   S 032e 0.25/0.00A: 01 0000 0019 0000  M: 00 0000 0000 0000
        #   S 032e 0.25/6.00A: 03 0258 0019 0000  M: 05 0000 0000 0000
        #   S 032e 0.25/0.00A: 01 0000 0019 0000  M: 00 0000 0000 0000
        #   S 032e 0.25/6.00A: 03 0258 0019 0000  M: 05 0000 0000 0000
        #
        # While it's doing this, it's continuously opening and closing the relay
        # on the TWC each second which makes an audible click and will wear out
        # the relay. To avoid that problem, always send code 05 when
        # desiredAmpsOffered == 0. In that case, slave's response should always
        # look like this:
        #   S 032e 0.25/0.00A: 03 0000 0019 0000 M: 05 0000 0000 0000
        if self.reportedAmpsMax != desiredAmpsOffered or desiredAmpsOffered == 0:
            desiredHundredthsOfAmps = int(desiredAmpsOffered * 100)
            self.masterHeartbeatData = bytearray(
                [
                    (0x09 if self.protocolVersion == 2 else 0x05),
                    (desiredHundredthsOfAmps >> 8) & 0xFF,
                    desiredHundredthsOfAmps & 0xFF,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                ]
            )
        else:
            self.masterHeartbeatData = bytearray(
                [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            )

        if len(self.master.getMasterHeartbeatOverride()) >= 7:
            self.masterHeartbeatData = self.master.getMasterHeartbeatOverride()

        if logger.getEffectiveLevel() <= logging.INFO:
            self.print_status(heartbeatData)

    def set_last_amps_offered(self, desiredAmpsOffered):
        # self.lastAmpsOffered should only be changed using this sub.

        logger.debug(
            "set_last_amps_offered(TWCID="
            + self.master.hex_str(self.TWCID)
            + ", desiredAmpsOffered="
            + str(desiredAmpsOffered)
            + ")"
        )

        if desiredAmpsOffered != self.lastAmpsOffered:
            oldLastAmpsOffered = self.lastAmpsOffered
            self.lastAmpsOffered = desiredAmpsOffered

            # Set totalAmpsAllTWCs to the total amps all TWCs are actually using
            # minus amps this TWC is using, plus amps this TWC wants to use.
            totalAmpsAllTWCs = (
                self.master.getTotalAmpsInUse()
                - self.reportedAmpsActual
                + self.lastAmpsOffered
            )
            if totalAmpsAllTWCs > self.config["config"]["wiringMaxAmpsAllTWCs"]:
                # totalAmpsAllTWCs would exceed wiringMaxAmpsAllTWCs if we
                # allowed this TWC to use desiredAmpsOffered.  Instead, try
                # offering as many amps as will increase total_amps_actual_all_twcs()
                # up to wiringMaxAmpsAllTWCs.
                self.lastAmpsOffered = int(
                    self.config["config"]["wiringMaxAmpsAllTWCs"]
                    - (self.master.getTotalAmpsInUse() - self.reportedAmpsActual)
                )

                if self.lastAmpsOffered < self.minAmpsTWCSupports:
                    # Always offer at least minAmpsTWCSupports amps.
                    # See notes in receive_slave_heartbeat() beneath
                    # 'if(maxAmpsToDivideAmongSlaves / numCarsCharging > minAmpsToOffer):'
                    self.lastAmpsOffered = self.minAmpsTWCSupports

                logger.info(
                    "WARNING: Offering slave TWC %02X%02X %.1fA instead of "
                    "%.1fA to avoid overloading wiring shared by all TWCs."
                    % (
                        self.TWCID[0],
                        self.TWCID[1],
                        self.lastAmpsOffered,
                        desiredAmpsOffered,
                    )
                )

            if self.lastAmpsOffered > self.wiringMaxAmps:
                # We reach this case frequently in some configurations, such as
                # when two 80A TWCs share a 125A line.  Therefore, don't print
                # an error.
                self.lastAmpsOffered = self.wiringMaxAmps
                logger.debug(
                    "Offering slave TWC %02X%02X %.1fA instead of "
                    "%.1fA to avoid overloading the TWC rated at %.1fA."
                    % (
                        self.TWCID[0],
                        self.TWCID[1],
                        self.lastAmpsOffered,
                        desiredAmpsOffered,
                        self.wiringMaxAmps,
                    )
                )

            if self.lastAmpsOffered != oldLastAmpsOffered:
                self.timeLastAmpsOfferedChanged = time.time()
        return self.lastAmpsOffered

    def setLifetimekWh(self, kwh):
        self.lifetimekWh = kwh
        # Publish Lifetime kWh Value via Status modules
        for module in self.master.getModulesByType("Status"):
            module["ref"].setStatus(
                self.TWCID, "lifetime_kwh", "lifetimekWh", self.lifetimekWh, "kWh"
            )

    def setVoltage(self, pa, pb, pc):
        self.voltsPhaseA = pa
        self.voltsPhaseB = pb
        self.voltsPhaseC = pc
        # Publish phase 1, 2 and 3 values via Status modules
        for phase in ("A", "B", "C"):
            for module in self.master.getModulesByType("Status"):
                module["ref"].setStatus(
                    self.TWCID,
                    "voltage_phase_" + phase.lower(),
                    "voltagePhase" + phase,
                    getattr(self, "voltsPhase" + phase, 0),
                    "V",
                )
        self.refreshingChargerLoadStatus()

    def refreshingChargerLoadStatus(self):
        for module in self.master.getModulesByType("Status"):
            module["ref"].setStatus(
                self.TWCID,
                "charger_load_w",
                "chargerLoadInW",
                int(self.getCurrentChargerLoad()),
                "W",
            )

    def getCurrentChargerLoad(self):
        return self.master.convertAmpsToWatts(
            self.reportedAmpsActual
        ) * self.master.getRealPowerFactor(self.reportedAmpsActual)

    def getLastVehicle(self):
        currentVehicle = None
        lastVehicle = None
        for vehicle in self.master.getModuleByName("TeslaAPI").getCarApiVehicles():
            if self.currentVIN == vehicle.VIN:
                currentVehicle = vehicle
            if self.lastVIN == vehicle.VIN:
                lastVehicle = vehicle
        if currentVehicle != None:
            return currentVehicle
        if lastVehicle != None:
            return lastVehicle
        return None
