#! /usr/bin/python3

################################################################################
# Code and TWC protocol reverse engineering by Chris Dragon.
#
# Additional logs and hints provided by Teslamotorsclub.com users:
#   TheNoOne, IanAmber, and twc.
# Thank you!
#
# For support and information, please read through this thread:
# https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830
#
# Report bugs at https://github.com/ngardiner/TWCManager/issues
#
# This software is released under the "Unlicense" model: http://unlicense.org
# This means source code and TWC protocol knowledge are released to the general
# public free for personal or commercial use. I hope the knowledge will be used
# to increase the use of green energy sources by controlling the time and power
# level of car charging.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please visit http://unlicense.org

import importlib
import logging
import os.path
import math
import re
import sys
import time
import traceback
import yaml
from datetime import datetime
import threading
from TWCManager.TWCMaster import TWCMaster
import requests
from enum import Enum


logging.addLevelName(19, "INFO2")
logging.addLevelName(18, "INFO4")
logging.addLevelName(17, "INFO4")
logging.addLevelName(16, "INFO5")
logging.addLevelName(15, "INFO6")
logging.addLevelName(14, "INFO7")
logging.addLevelName(13, "INFO8")
logging.addLevelName(12, "INFO9")
logging.addLevelName(9, "DEBUG2")
logging.INFO2 = 19
logging.INFO3 = 18
logging.INFO4 = 17
logging.INFO5 = 16
logging.INFO6 = 15
logging.INFO7 = 14
logging.INFO8 = 13
logging.INFO9 = 12
logging.DEBUG2 = 9


logger = logging.getLogger("\u26FD Manager")

# Define available modules for the instantiator
# All listed modules will be loaded at boot time
# Logging modules should be the first one to load
modules_available = [
    "Logging.ConsoleLogging",
    "Logging.FileLogging",
    "Logging.SentryLogging",
    "Logging.CSVLogging",
    "Logging.MySQLLogging",
    "Logging.SQLiteLogging",
    "Protocol.TWCProtocol",
    "Interface.Dummy",
    "Interface.RS485",
    "Interface.TCP",
    "Policy.Policy",
    "Vehicle.TeslaAPI",
    "Vehicle.TeslaMateVehicle",
    "Control.WebIPCControl",
    "Control.HTTPControl",
    "Control.MQTTControl",
    #    "Control.OCPPControl",
    "EMS.Efergy",
    "EMS.EmonCMS",
    "EMS.Enphase",
    "EMS.Fronius",
    "EMS.Growatt",
    "EMS.HASS",
    "EMS.IotaWatt",
    "EMS.Kostal",
    "EMS.OpenHab",
    "EMS.OpenWeatherMap",
    "EMS.P1Monitor",
    "EMS.SmartMe",
    "EMS.SmartPi",
    "EMS.SolarEdge",
    "EMS.SolarLog",
    "EMS.TeslaPowerwall2",
    "EMS.TED",
    "EMS.Volkszahler",
    "EMS.URL",
    "Status.HASSStatus",
    "Status.MQTTStatus",
]

# Enable support for Python Visual Studio Debugger
if "DEBUG_SECRET" in os.environ:
    import ptvsd

    ptvsd.enable_attach(os.environ["DEBUG_SECRET"])
    ptvsd.wait_for_attach()

##########################
# Load Configuration File
config = None
jsonconfig = None
if os.path.isfile("/etc/twcmanager/config.json"):
    jsonconfig = open("/etc/twcmanager/config.json")
else:
    if os.path.isfile("config.json"):
        jsonconfig = open("config.json")

if jsonconfig:
    configtext = ""
    for line in jsonconfig:
        if line.lstrip().startswith("//") or line.lstrip().startswith("#"):
            configtext += "\n"
        else:
            configtext += line.replace("\t", " ").split("#")[0]

    config = yaml.safe_load(configtext)
    configtext = None
else:
    logger.error("Unable to find a configuration file.")
    sys.exit()


logLevel = config["config"].get("logLevel")
if logLevel == None:
    debugLevel = config["config"].get("debugLevel", 1)
    debug_to_log = {
        0: 40,
        1: 20,
        2: 19,
        3: 18,
        4: 17,
        5: 16,
        6: 15,
        7: 14,
        8: 13,
        9: 12,
        10: 10,
        11: 9,
    }
    for debug, log in debug_to_log.items():
        if debug >= debugLevel:
            logLevel = log
            break

logging.getLogger().setLevel(logLevel)

# All TWCs ship with a random two-byte TWCID. We default to using 0x7777 as our
# fake TWC ID. There is a 1 in 64535 chance that this ID will match each real
# TWC on the network, in which case you should pick a different random id below.
# This isn't really too important because even if this ID matches another TWC on
# the network, that TWC will pick its own new random ID as soon as it sees ours
# conflicts.
fakeTWCID = bytearray(b"\x77\x77")

#
# End configuration parameters
#
##############################


##############################
#
# Begin functions
#


def hex_str(s: str):
    return " ".join("{:02X}".format(ord(c)) for c in s)


def hex_str(ba: bytearray):
    return " ".join("{:02X}".format(c) for c in ba)


def time_now():
    global config
    return datetime.now().strftime(
        "%H:%M:%S" + (".%f" if config["config"]["displayMilliseconds"] else "")
    )


def unescape_msg(inmsg: bytearray, msgLen):
    # Given a message received on the RS485 network, remove leading and trailing
    # C0 byte, unescape special byte values, and verify its data matches the CRC
    # byte.

    # Note that a bytearray is mutable, whereas a bytes object isn't.
    # By initializing a bytearray and concatenating the incoming bytearray
    # to it, we protect against being passed an immutable bytes object
    msg = bytearray() + inmsg[0:msgLen]

    # See notes in RS485.send() for the way certain bytes in messages are escaped.
    # We basically want to change db dc into c0 and db dd into db.
    # Only scan to one less than the length of the string to avoid running off
    # the end looking at i+1.
    i = 0
    while i < len(msg):
        if msg[i] == 0xDB:
            if msg[i + 1] == 0xDC:
                # Replace characters at msg[i] and msg[i+1] with 0xc0,
                # shortening the string by one character. In Python, msg[x:y]
                # refers to a substring starting at x and ending immediately
                # before y. y - x is the length of the substring.
                msg[i : i + 2] = [0xC0]
            elif msg[i + 1] == 0xDD:
                msg[i : i + 2] = [0xDB]
            else:
                logger.info(
                    "ERROR: Special character 0xDB in message is "
                    "followed by invalid character 0x%02X.  "
                    "Message may be corrupted." % (msg[i + 1])
                )

                # Replace the character with something even though it's probably
                # not the right thing.
                msg[i : i + 2] = [0xDB]
        i = i + 1

    # Remove leading and trailing C0 byte.
    msg = msg[1 : len(msg) - 1]
    return msg


def background_tasks_thread(master):
    carapi = master.getModuleByName("TeslaAPI")

    while True:
        try:
            task = master.getBackgroundTask()

            if "cmd" in task:
                if task["cmd"] == "applyChargeLimit":
                    carapi.applyChargeLimit(limit=task["limit"])
                elif task["cmd"] == "charge":
                    # car_api_charge does nothing if it's been under 60 secs since it
                    # was last used so we shouldn't have to worry about calling this
                    # too frequently.
                    carapi.car_api_charge(task["charge"])
                elif task["cmd"] == "carApiEmailPassword":
                    carapi.resetCarApiLastErrorTime()
                    carapi.car_api_available(task["email"], task["password"])
                elif task["cmd"] == "checkArrival":
                    limit = (
                        carapi.lastChargeLimitApplied
                        if carapi.lastChargeLimitApplied != 0
                        else -1
                    )
                    carapi.applyChargeLimit(limit=limit, checkArrival=True)
                elif task["cmd"] == "checkCharge":
                    carapi.updateChargeAtHome()
                elif task["cmd"] == "checkDeparture":
                    carapi.applyChargeLimit(
                        limit=carapi.lastChargeLimitApplied, checkDeparture=True
                    )
                elif task["cmd"] == "checkGreenEnergy":
                    check_green_energy()
                elif task["cmd"] == "checkVINEntitlement":
                    # The two possible arguments are task["subTWC"] which tells us
                    # which TWC to check, or task["vin"] which tells us which VIN
                    if task.get("vin", None):
                        task["subTWC"] = master.getTWCbyVIN(task["vin"])

                    if task["subTWC"]:
                        if master.checkVINEntitlement(task["subTWC"]):
                            logger.info(
                                "Vehicle %s on TWC %02X%02X is permitted to charge."
                                % (
                                    task["subTWC"].currentVIN,
                                    task["subTWC"].TWCID[0],
                                    task["subTWC"].TWCID[1],
                                )
                            )
                        else:
                            logger.info(
                                "Vehicle %s on TWC %02X%02X is not permitted to charge. Terminating session."
                                % (
                                    task["subTWC"].currentVIN,
                                    task["subTWC"].TWCID[0],
                                    task["subTWC"].TWCID[1],
                                )
                            )
                            master.sendStopCommand(task["subTWC"].TWCID)

                elif task["cmd"] == "getLifetimekWh":
                    master.getSlaveLifetimekWh()
                elif task["cmd"] == "getVehicleVIN":
                    master.getVehicleVIN(task["slaveTWC"], task["vinPart"])
                elif task["cmd"] == "snapHistoryData":
                    master.snapHistoryData()
                elif task["cmd"] == "updateStatus":
                    update_statuses()
                elif task["cmd"] == "webhook":
                    if config["config"].get("webhookMethod", "POST") == "GET":
                        requests.get(task["url"])
                    else:
                        body = master.getStatus()
                        requests.post(task["url"], json=body)
                elif task["cmd"] == "saveSettings":
                    master.saveSettings()

        except:
            logger.info(
                "%s: "
                + traceback.format_exc()
                + ", occurred when processing background task",
                "BackgroundError",
                extra={"colored": "red"},
            )
            pass

        # task_done() must be called to let the queue know the task is finished.
        # backgroundTasksQueue.join() can then be used to block until all tasks
        # in the queue are done.
        master.doneBackgroundTask(task)


def check_green_energy():
    global config, hass, master

    # Check solar panel generation using an API exposed by
    # the HomeAssistant API.
    #
    # You may need to customize the sensor entity_id values
    # to match those used in your environment. This is configured
    # in the config section at the top of this file.
    #

    # Poll all loaded EMS modules for consumption and generation values
    for module in master.getModulesByType("EMS"):
        master.setConsumption(module["name"], module["ref"].getConsumption())
        master.setGeneration(module["name"], module["ref"].getGeneration())

    # Set max amps iff charge_amps isn't specified on the policy.
    if master.getModuleByName("Policy").policyIsGreen():
        master.setMaxAmpsToDivideAmongSlaves(master.getMaxAmpsToDivideGreenEnergy())


def update_statuses():

    # Print a status update if we are on track green energy showing the
    # generation and consumption figures
    maxamps = master.getMaxAmpsToDivideAmongSlaves()
    maxampsDisplay = f"{maxamps:.2f}A"
    if master.getModuleByName("Policy").policyIsGreen():
        genwatts = master.getGeneration()
        conwatts = master.getConsumption()
        conoffset = master.getConsumptionOffset()
        chgwatts = master.getChargerLoad()
        othwatts = 0

        if config["config"]["subtractChargerLoad"]:
            if conwatts > 0:
                othwatts = conwatts - chgwatts

            if conoffset > 0:
                othwatts -= conoffset

        # Extra parameters to send with logs
        logExtra = {
            "logtype": "green_energy",
            "genWatts": genwatts,
            "conWatts": conwatts,
            "chgWatts": chgwatts,
            "colored": "magenta",
        }

        if (genwatts or conwatts) and (not conoffset and not othwatts):

            logger.info(
                "Green energy Generates %s, Consumption %s (Charger Load %s)",
                f"{genwatts:.0f}W",
                f"{conwatts:.0f}W",
                f"{chgwatts:.0f}W",
                extra=logExtra,
            )

        elif (genwatts or conwatts) and othwatts and not conoffset:

            logger.info(
                "Green energy Generates %s, Consumption %s (Charger Load %s, Other Load %s)",
                f"{genwatts:.0f}W",
                f"{conwatts:.0f}W",
                f"{chgwatts:.0f}W",
                f"{othwatts:.0f}W",
                extra=logExtra,
            )

        elif (genwatts or conwatts) and othwatts and conoffset > 0:

            logger.info(
                "Green energy Generates %s, Consumption %s (Charger Load %s, Other Load %s, Offset %s)",
                f"{genwatts:.0f}W",
                f"{conwatts:.0f}W",
                f"{chgwatts:.0f}W",
                f"{othwatts:.0f}W",
                f"{conoffset:.0f}W",
                extra=logExtra,
            )

        elif (genwatts or conwatts) and othwatts and conoffset < 0:

            logger.info(
                "Green energy Generates %s (Offset %s), Consumption %s (Charger Load %s, Other Load %s)",
                f"{genwatts:.0f}W",
                f"{(-1 * conoffset):.0f}W",
                f"{conwatts:.0f}W",
                f"{chgwatts:.0f}W",
                f"{othwatts:.0f}W",
                extra=logExtra,
            )

        nominalOffer = master.convertWattsToAmps(
            genwatts
            + (
                chgwatts
                if (config["config"]["subtractChargerLoad"] and conwatts == 0)
                else 0
            )
            - (
                conwatts
                - (
                    chgwatts
                    if (config["config"]["subtractChargerLoad"] and conwatts > 0)
                    else 0
                )
            )
        )
        if abs(maxamps - nominalOffer) > 0.005:
            nominalOfferDisplay = f"{nominalOffer:.2f}A"
            logger.debug(
                f"Offering {maxampsDisplay} instead of {nominalOfferDisplay} to compensate for inexact current draw"
            )
            conwatts = genwatts - master.convertAmpsToWatts(maxamps)
        generation = f"{master.convertWattsToAmps(genwatts):.2f}A"
        consumption = f"{master.convertWattsToAmps(conwatts):.2f}A"
        logger.info(
            "Limiting charging to %s - %s = %s.",
            generation,
            consumption,
            maxampsDisplay,
            extra={"colored": "magenta"},
        )

    else:
        # For all other modes, simply show the Amps to charge at
        logger.info(
            "Limiting charging to %s.", maxampsDisplay, extra={"colored": "magenta"}
        )

    # Print minimum charge for all charging policies
    minchg = f"{config['config']['minAmpsPerTWC']}A"
    logger.info(
        "Charge when above %s (minAmpsPerTWC).", minchg, extra={"colored": "magenta"}
    )

    # Update Sensors with min/max amp values
    for module in master.getModulesByType("Status"):
        module["ref"].setStatus(
            bytes("config", "UTF-8"),
            "min_amps_per_twc",
            "minAmpsPerTWC",
            config["config"]["minAmpsPerTWC"],
            "A",
        )
        module["ref"].setStatus(
            bytes("all", "UTF-8"),
            "max_amps_for_slaves",
            "maxAmpsForSlaves",
            master.getMaxAmpsToDivideAmongSlaves(),
            "A",
        )


#
# End functions
#
##############################

##############################
#
# Begin global vars
#

data = ""
dataLen = 0
ignoredData = bytearray()
msg = bytearray()
msgLen = 0

numInitMsgsToSend = 10
msgRxCount = 0

idxSlaveToSendNextHeartbeat = 0
timeLastkWhDelivered = time.time()
timeLastkWhSaved = time.time()
timeLastHeartbeatDebugOutput = 0

webMsgPacked = ""
webMsgMaxSize = 300
webMsgResult = 0

timeTo0Aafter06 = 0
timeToRaise2A = 0

#
# End global vars
#
##############################


##############################
#
# Begin main program
#

# Instantiate necessary classes
master = TWCMaster(fakeTWCID, config)

# Instantiate all modules in the modules_available list automatically
for module in modules_available:
    modulename = []
    if str(module).find(".") != -1:
        modulename = str(module).split(".")

    try:
        # Pre-emptively skip modules that we know are not configured
        configlocation = master.translateModuleNameToConfig(modulename)
        if (
            not config.get(configlocation[0], {})
            .get(configlocation[1], {})
            .get("enabled", 1)
        ):
            # We can see that this module is explicitly disabled in config, skip it
            continue

        moduleref = importlib.import_module("TWCManager." + module)
        modclassref = getattr(moduleref, modulename[1])
        modinstance = modclassref(master)

        # Register the new module with master class, so every other module can
        # interact with it
        master.registerModule(
            {"name": modulename[1], "ref": modinstance, "type": modulename[0]}
        )
    except ImportError as e:
        logger.error(
            "%s: " + str(e) + ", when importing %s, not using %s",
            "ImportError",
            module,
            module,
            extra={"colored": "red"},
        )
    except ModuleNotFoundError as e:
        logger.info(
            "%s: " + str(e) + ", when importing %s, not using %s",
            "ModuleNotFoundError",
            module,
            module,
            extra={"colored": "red"},
        )
    except:
        raise


# Load settings from file
master.loadSettings()

# Create a background thread to handle tasks that take too long on the main
# thread.  For a primer on threads in Python, see:
# http://www.laurentluce.com/posts/python-threads-synchronization-locks-rlocks-semaphores-conditions-events-and-queues/
backgroundTasksThread = threading.Thread(target=background_tasks_thread, args=(master,))
backgroundTasksThread.daemon = True
backgroundTasksThread.start()

logger.info(
    "TWC Manager starting as fake %s with id %02X%02X and sign %02X"
    % (
        ("Master" if config["config"]["fakeMaster"] else "Slave"),
        ord(fakeTWCID[0:1]),
        ord(fakeTWCID[1:2]),
        ord(master.getSlaveSign()),
    )
)

while True:
    try:
        # In this area, we always send a linkready message when we first start.
        # Whenever there is no data available from other TWCs to respond to,
        # we'll loop back to this point to send another linkready or heartbeat
        # message. By only sending our periodic messages when no incoming
        # message data is available, we reduce the chance that we will start
        # transmitting a message in the middle of an incoming message, which
        # would corrupt both messages.

        # Add a 25ms sleep to prevent pegging pi's CPU at 100%. Lower CPU means
        # less power used and less waste heat.
        time.sleep(0.025)

        now = time.time()

        if config["config"]["fakeMaster"] == 1:
            # A real master sends 5 copies of linkready1 and linkready2 whenever
            # it starts up, which we do here.
            # It doesn't seem to matter if we send these once per second or once
            # per 100ms so I do once per 100ms to get them over with.
            if numInitMsgsToSend > 5:
                master.send_master_linkready1()
                time.sleep(0.1)  # give slave time to respond
                numInitMsgsToSend -= 1
            elif numInitMsgsToSend > 0:
                master.send_master_linkready2()
                time.sleep(0.1)  # give slave time to respond
                numInitMsgsToSend = numInitMsgsToSend - 1
            else:
                # After finishing the 5 startup linkready1 and linkready2
                # messages, master will send a heartbeat message to every slave
                # it's received a linkready message from. Do that here.
                # A real master would keep sending linkready messages periodically
                # as long as no slave was connected, but since real slaves send
                # linkready once every 10 seconds till they're connected to a
                # master, we'll just wait for that.
                if time.time() - master.getTimeLastTx() >= 1.0:
                    # It's been about a second since our last heartbeat.
                    if master.countSlaveTWC() > 0:
                        slaveTWC = master.getSlaveTWC(idxSlaveToSendNextHeartbeat)
                        if time.time() - slaveTWC.timeLastRx > 26:
                            # A real master stops sending heartbeats to a slave
                            # that hasn't responded for ~26 seconds. It may
                            # still send the slave a heartbeat every once in
                            # awhile but we're just going to scratch the slave
                            # from our little black book and add them again if
                            # they ever send us a linkready.
                            logger.info(
                                "WARNING: We haven't heard from slave "
                                "%02X%02X for over 26 seconds.  "
                                "Stop sending them heartbeat messages."
                                % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
                            )
                            master.deleteSlaveTWC(slaveTWC.TWCID)
                        else:
                            slaveTWC.send_master_heartbeat()

                        idxSlaveToSendNextHeartbeat = idxSlaveToSendNextHeartbeat + 1
                        if idxSlaveToSendNextHeartbeat >= master.countSlaveTWC():
                            idxSlaveToSendNextHeartbeat = 0
                        time.sleep(0.1)  # give slave time to respond
        else:
            # As long as a slave is running, it sends link ready messages every
            # 10 seconds. They trigger any master on the network to handshake
            # with the slave and the master then sends a status update from the
            # slave every 1-3 seconds. Master's status updates trigger the slave
            # to send back its own status update.
            # As long as master has sent a status update within the last 10
            # seconds, slaves don't send link ready.
            # I've also verified that masters don't care if we stop sending link
            # ready as long as we send status updates in response to master's
            # status updates.
            if (
                config["config"]["fakeMaster"] != 2
                and time.time() - master.getTimeLastTx() >= 10.0
            ):
                logger.info(
                    "Advertise fake slave %02X%02X with sign %02X is "
                    "ready to link once per 10 seconds as long as master "
                    "hasn't sent a heartbeat in the last 10 seconds."
                    % (
                        ord(fakeTWCID[0:1]),
                        ord(fakeTWCID[1:2]),
                        ord(master.getSlaveSign()),
                    )
                )
                master.send_slave_linkready()

        # See if there's any message from the web interface.
        if master.getModuleByName("WebIPCControl"):
            master.getModuleByName("WebIPCControl").processIPC()

        # If it has been more than 2 minutes since the last kWh value,
        # queue the command to request it from slaves
        if config["config"]["fakeMaster"] == 1 and (
            (time.time() - master.lastkWhMessage) > (60 * 2)
        ):
            master.lastkWhMessage = time.time()
            master.queue_background_task({"cmd": "getLifetimekWh"})

        # If it has been more than 1 minute since the last VIN query with no
        # response, and if we haven't queried more than 5 times already for this
        # slave TWC, repeat the query
        master.retryVINQuery()

        ########################################################################
        # See if there's an incoming message on the input interface.

        timeMsgRxStart = time.time()
        actualDataLen = 0
        while True:
            now = time.time()
            dataLen = master.getInterfaceModule().getBufferLen()
            if dataLen == 0:
                if msgLen == 0:
                    # No message data waiting and we haven't received the
                    # start of a new message yet. Break out of inner while
                    # to continue at top of outer while loop where we may
                    # decide to send a periodic message.
                    break
                else:
                    # No message data waiting but we've received a partial
                    # message that we should wait to finish receiving.
                    if now - timeMsgRxStart >= 2.0:
                        logger.log(
                            logging.INFO9,
                            "Msg timeout ("
                            + hex_str(ignoredData)
                            + ") "
                            + hex_str(msg[0:msgLen]),
                        )
                        msgLen = 0
                        ignoredData = bytearray()
                        break

                    time.sleep(0.025)
                    continue
            else:
                actualDataLen = dataLen
                dataLen = 1
                data = master.getInterfaceModule().read(dataLen)

            if dataLen != 1:
                # This should never happen
                logger.info("WARNING: No data available.")
                break

            timeMsgRxStart = now
            timeLastRx = now
            if msgLen == 0 and len(data) > 0 and data[0] != 0xC0:
                # We expect to find these non-c0 bytes between messages, so
                # we don't print any warning at standard debug levels.
                logger.log(
                    logging.DEBUG2, "Ignoring byte %02X between messages." % (data[0])
                )
                ignoredData += data
                continue
            elif msgLen > 0 and msgLen < 15 and len(data) > 0 and data[0] == 0xC0:
                # If you see this when the program is first started, it
                # means we started listening in the middle of the TWC
                # sending a message so we didn't see the whole message and
                # must discard it. That's unavoidable.
                # If you see this any other time, it means there was some
                # corruption in what we received. It's normal for that to
                # happen every once in awhile but there may be a problem
                # such as incorrect termination or bias resistors on the
                # rs485 wiring if you see it frequently.
                logger.debug(
                    "Found end of message before full-length message received.  "
                    "Discard and wait for new message."
                )

                msg = data
                msgLen = 1
                continue
            elif dataLen and len(data) == 0:
                logger.error(
                    "We received a buffer length of %s from the RS485 module, but data buffer length is %s. This should not occur."
                    % (str(actualDataLen), str(len(data)))
                )

            if msgLen == 0:
                msg = bytearray()
            msg += data
            msgLen += 1

            # Messages are usually 17 bytes or longer and end with \xc0\xfe.
            # However, when the network lacks termination and bias
            # resistors, the last byte (\xfe) may be corrupted or even
            # missing, and you may receive additional garbage bytes between
            # messages.
            #
            # TWCs seem to account for corruption at the end and between
            # messages by simply ignoring anything after the final \xc0 in a
            # message, so we use the same tactic. If c0 happens to be within
            # the corrupt noise between messages, we ignore it by starting a
            # new message whenever we see a c0 before 15 or more bytes are
            # received.
            #
            # Uncorrupted messages can be over 17 bytes long when special
            # values are "escaped" as two bytes. See notes in sendMsg.
            #
            # To prevent most noise between messages, add a 120ohm
            # "termination" resistor in parallel to the D+ and D- lines.
            # Also add a 680ohm "bias" resistor between the D+ line and +5V
            # and a second 680ohm "bias" resistor between the D- line and
            # ground. See here for more information:
            #   https://www.ni.com/support/serial/resinfo.htm
            #   http://www.ti.com/lit/an/slyt514/slyt514.pdf
            # This explains what happens without "termination" resistors:
            #   https://e2e.ti.com/blogs_/b/analogwire/archive/2016/07/28/rs-485-basics-when-termination-is-necessary-and-how-to-do-it-properly
            if msgLen >= 16 and data[0] == 0xC0:
                break

        if msgLen >= 16:
            msg = unescape_msg(msg, msgLen)
            # Set msgLen = 0 at start so we don't have to do it on errors below.
            # len($msg) now contains the unescaped message length.
            msgLen = 0

            msgRxCount += 1

            # When the sendTWCMsg web command is used to send a message to the
            # TWC, it sets lastTWCResponseMsg = b''.  When we see that here,
            # set lastTWCResponseMsg to any unusual message received in response
            # to the sent message.  Never set lastTWCResponseMsg to a commonly
            # repeated message like master or slave linkready, heartbeat, or
            # voltage/kWh report.
            if (
                master.lastTWCResponseMsg == b""
                and msg[0:2] != b"\xFB\xE0"
                and msg[0:2] != b"\xFD\xE0"
                and msg[0:2] != b"\xFC\xE1"
                and msg[0:2] != b"\xFB\xE2"
                and msg[0:2] != b"\xFD\xE2"
                and msg[0:2] != b"\xFB\xEB"
                and msg[0:2] != b"\xFD\xEB"
                and msg[0:2] != b"\xFD\xE0"
            ):
                master.lastTWCResponseMsg = msg

            logger.log(
                logging.INFO9,
                "Rx@" + ": (" + hex_str(ignoredData) + ") " + hex_str(msg) + "",
            )

            ignoredData = bytearray()

            # After unescaping special values and removing the leading and
            # trailing C0 bytes, the messages we know about are always 14 bytes
            # long in original TWCs, or 16 bytes in newer TWCs (protocolVersion
            # == 2).
            if len(msg) != 14 and len(msg) != 16 and len(msg) != 20:
                logger.info(
                    "ERROR: Ignoring message of unexpected length %d: %s"
                    % (len(msg), hex_str(msg))
                )
                continue

            checksumExpected = msg[len(msg) - 1]
            checksum = 0
            for i in range(1, len(msg) - 1):
                checksum += msg[i]

            if (checksum & 0xFF) != checksumExpected:
                logger.info(
                    "ERROR: Checksum %X does not match %02X.  Ignoring message: %s"
                    % (checksum, checksumExpected, hex_str(msg))
                )
                continue

            if config["config"]["fakeMaster"] == 1:
                ############################
                # Pretend to be a master TWC

                foundMsgMatch = False
                # We end each regex message search below with \Z instead of $
                # because $ will match a newline at the end of the string or the
                # end of the string (even without the re.MULTILINE option), and
                # sometimes our strings do end with a newline character that is
                # actually the CRC byte with a value of 0A or 0D.
                msgMatch = re.search(b"^\xfd\xb1(..)\x00\x00.+\Z", msg, re.DOTALL)
                if msgMatch and foundMsgMatch == False:
                    # Handle acknowledgement of Start command
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)

                msgMatch = re.search(b"^\xfd\xb2(..)\x00\x00.+\Z", msg, re.DOTALL)
                if msgMatch and foundMsgMatch == False:
                    # Handle acknowledgement of Stop command
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)

                msgMatch = re.search(
                    b"^\xfd\xe2(..)(.)(..)\x00\x00\x00\x00\x00\x00.+\Z", msg, re.DOTALL
                )
                if msgMatch and foundMsgMatch == False:
                    # Handle linkready message from slave.
                    #
                    # We expect to see one of these before we start sending our
                    # own heartbeat message to slave.
                    # Once we start sending our heartbeat to slave once per
                    # second, it should no longer send these linkready messages.
                    # If slave doesn't hear master's heartbeat for around 10
                    # seconds, it sends linkready once per 10 seconds and starts
                    # flashing its red LED 4 times with the top green light on.
                    # Red LED stops flashing if we start sending heartbeat
                    # again.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    sign = msgMatch.group(2)
                    maxAmps = ((msgMatch.group(3)[0] << 8) + msgMatch.group(3)[1]) / 100

                    logger.info(
                        "%.2f amp slave TWC %02X%02X is ready to link.  Sign: %s"
                        % (maxAmps, senderID[0], senderID[1], hex_str(sign))
                    )

                    if maxAmps >= 80:
                        # U.S. chargers need a spike to 21A to cancel a 6A
                        # charging limit imposed in an Oct 2017 Tesla car
                        # firmware update. See notes where
                        # spikeAmpsToCancel6ALimit is used.
                        master.setSpikeAmps(21)
                    else:
                        # EU chargers need a spike to only 16A.  This value
                        # comes from a forum post and has not been directly
                        # tested.
                        master.setSpikeAmps(16)

                    if senderID == fakeTWCID:
                        logger.info(
                            "Slave TWC %02X%02X reports same TWCID as master.  "
                            "Slave should resolve by changing its TWCID."
                            % (senderID[0], senderID[1])
                        )
                        # I tested sending a linkready to a real master with the
                        # same TWCID as master and instead of master sending back
                        # its heartbeat message, it sent 5 copies of its
                        # linkready1 and linkready2 messages. Those messages
                        # will prompt a real slave to pick a new random value
                        # for its TWCID.
                        #
                        # We mimic that behavior by setting numInitMsgsToSend =
                        # 10 to make the idle code at the top of the for()
                        # loop send 5 copies of linkready1 and linkready2.
                        numInitMsgsToSend = 10
                        continue

                    # We should always get this linkready message at least once
                    # and generally no more than once, so this is a good
                    # opportunity to add the slave to our known pool of slave
                    # devices.
                    slaveTWC = master.newSlave(senderID, maxAmps)

                    if (
                        slaveTWC.protocolVersion == 1
                        and slaveTWC.minAmpsTWCSupports == 6
                    ):
                        if len(msg) == 14:
                            slaveTWC.protocolVersion = 1
                            slaveTWC.minAmpsTWCSupports = 5
                        elif len(msg) == 16:
                            slaveTWC.protocolVersion = 2
                            slaveTWC.minAmpsTWCSupports = 6

                        logger.info(
                            "Set slave TWC %02X%02X protocolVersion to %d, minAmpsTWCSupports to %d."
                            % (
                                senderID[0],
                                senderID[1],
                                slaveTWC.protocolVersion,
                                slaveTWC.minAmpsTWCSupports,
                            )
                        )

                    # We expect maxAmps to be 80 on U.S. chargers and 32 on EU
                    # chargers. Either way, don't allow
                    # slaveTWC.wiringMaxAmps to be greater than maxAmps.
                    if slaveTWC.wiringMaxAmps > maxAmps:
                        logger.info(
                            "\n\n!!! DANGER DANGER !!!\nYou have set wiringMaxAmpsPerTWC to "
                            + str(config["config"]["wiringMaxAmpsPerTWC"])
                            + " which is greater than the max "
                            + str(maxAmps)
                            + " amps your charger says it can handle.  "
                            "Please review instructions in the source code and consult an "
                            "electrician if you don't know what to do."
                        )
                        slaveTWC.wiringMaxAmps = maxAmps / 4

                    # Make sure we print one SHB message after a slave
                    # linkready message is received by clearing
                    # lastHeartbeatDebugOutput. This helps with debugging
                    # cases where I can't tell if we responded with a
                    # heartbeat or not.
                    slaveTWC.lastHeartbeatDebugOutput = ""

                    slaveTWC.timeLastRx = time.time()
                    slaveTWC.send_master_heartbeat()
                else:
                    msgMatch = re.search(
                        b"\A\xfd\xe0(..)(..)(.......+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle heartbeat message from slave.
                    #
                    # These messages come in as a direct response to each
                    # heartbeat message from master. Slave does not send its
                    # heartbeat until it gets one from master first.
                    # A real master sends heartbeat to a slave around once per
                    # second, so we do the same near the top of this for()
                    # loop. Thus, we should receive a heartbeat reply from the
                    # slave around once per second as well.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    receiverID = msgMatch.group(2)
                    heartbeatData = msgMatch.group(3)

                    try:
                        slaveTWC = master.getSlaveByID(senderID)
                    except KeyError:
                        # Normally, a slave only sends us a heartbeat message if
                        # we send them ours first, so it's not expected we would
                        # hear heartbeat from a slave that's not in our list.
                        logger.info(
                            "ERROR: Received heartbeat message from "
                            "slave %02X%02X that we've not met before."
                            % (senderID[0], senderID[1])
                        )
                        continue

                    if fakeTWCID == receiverID:
                        slaveTWC.receive_slave_heartbeat(heartbeatData)
                    else:
                        # I've tried different fakeTWCID values to verify a
                        # slave will send our fakeTWCID back to us as
                        # receiverID. However, I once saw it send receiverID =
                        # 0000.
                        # I'm not sure why it sent 0000 and it only happened
                        # once so far, so it could have been corruption in the
                        # data or an unusual case.
                        logger.info(
                            "WARNING: Slave TWC %02X%02X status data: "
                            "%s sent to unknown TWC %02X%02X."
                            % (
                                senderID[0],
                                senderID[1],
                                hex_str(heartbeatData),
                                receiverID[0],
                                receiverID[1],
                            )
                        )
                else:
                    msgMatch = re.search(
                        b"\A\xfd\xeb(..)(....)(..)(..)(..)(.+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle kWh total and voltage message from slave.
                    #
                    # This message can only be generated by TWCs running newer
                    # firmware.  I believe it's only sent as a response to a
                    # message from Master in this format:
                    #   FB EB <Master TWCID> <Slave TWCID> 00 00 00 00 00 00 00 00 00
                    # According to FuzzyLogic, this message has the following
                    # format on an EU (3-phase) TWC:
                    #   FD EB <Slave TWCID> 00000038 00E6 00F1 00E8 00
                    #   00000038 (56) is the total kWh delivered to cars
                    #     by this TWC since its construction.
                    #   00E6 (230) is voltage on phase A
                    #   00F1 (241) is voltage on phase B
                    #   00E8 (232) is voltage on phase C
                    #
                    # I'm guessing in world regions with two-phase power that
                    # this message would be four bytes shorter, but the pattern
                    # above will match a message of any length that starts with
                    # FD EB.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    lifetimekWh = msgMatch.group(2)
                    kWh = (
                        (lifetimekWh[0] << 24)
                        + (lifetimekWh[1] << 16)
                        + (lifetimekWh[2] << 8)
                        + lifetimekWh[3]
                    )
                    vPhaseA = msgMatch.group(3)
                    voltsPhaseA = (vPhaseA[0] << 8) + vPhaseA[1]
                    vPhaseB = msgMatch.group(4)
                    voltsPhaseB = (vPhaseB[0] << 8) + vPhaseB[1]
                    vPhaseC = msgMatch.group(5)
                    voltsPhaseC = (vPhaseC[0] << 8) + vPhaseC[1]
                    data = msgMatch.group(6)

                    logger.info(
                        "Slave TWC %02X%02X: Delivered %d kWh, voltage per phase: (%d, %d, %d).",
                        senderID[0],
                        senderID[1],
                        kWh,
                        voltsPhaseA,
                        voltsPhaseB,
                        voltsPhaseC,
                        extra={
                            "logtype": "slave_status",
                            "TWCID": senderID,
                            "kWh": kWh,
                            "voltsPerPhase": [voltsPhaseA, voltsPhaseB, voltsPhaseC],
                        },
                    )

                    # Update the timestamp of the last reciept of this message
                    master.lastkWhMessage = time.time()

                    # Every time we get this message, we re-queue the query
                    master.queue_background_task({"cmd": "getLifetimekWh"})

                    # Update this detail for the Slave TWC
                    master.updateSlaveLifetime(
                        senderID, kWh, voltsPhaseA, voltsPhaseB, voltsPhaseC
                    )

                else:
                    msgMatch = re.search(
                        b"\A\xfd(\xee|\xef|\xf1)(..)(.+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Get 7 characters of VIN from slave. (XE is first 7, XF second 7)
                    #
                    # This message can only be generated by TWCs running newer
                    # firmware.  I believe it's only sent as a response to a
                    # message from Master in this format:
                    #   FB EE <Master TWCID> <Slave TWCID> 00 00 00 00 00 00 00 00 00

                    # Response message is FD EE <Slave TWCID> VV VV VV VV VV VV VV where VV is an ascii character code
                    # representing a letter or number. VV will be all zero when car CAN communication is disabled
                    # (DIP switch 2 down) or when a non-Tesla vehicle is plugged in using something like a JDapter.

                    foundMsgMatch = True
                    vinPart = msgMatch.group(1)
                    senderID = msgMatch.group(2)
                    data = msgMatch.group(3)

                    logger.log(
                        logging.INFO6,
                        "Slave TWC %02X%02X reported VIN data: %s."
                        % (senderID[0], senderID[1], hex_str(data)),
                    )
                    slaveTWC = master.getSlaveByID(senderID)
                    if vinPart == b"\xee":
                        vinPart = 0
                    if vinPart == b"\xef":
                        vinPart = 1
                    if vinPart == b"\xf1":
                        vinPart = 2
                    slaveTWC.VINData[vinPart] = data.decode("utf-8").rstrip("\x00")
                    if vinPart < 2:
                        vinPart += 1
                        master.queue_background_task(
                            {
                                "cmd": "getVehicleVIN",
                                "slaveTWC": senderID,
                                "vinPart": str(vinPart),
                            }
                        )
                    else:
                        potentialVIN = "".join(slaveTWC.VINData)

                        # Ensure we have a valid VIN
                        if len(potentialVIN) == 17:
                            # Record Vehicle VIN
                            slaveTWC.currentVIN = potentialVIN

                            # Clear VIN retry timer
                            slaveTWC.lastVINQuery = 0
                            slaveTWC.vinQueryAttempt = 0

                            # Record this vehicle being connected
                            master.recordVehicleVIN(slaveTWC)

                            # Send VIN data to Status modules
                            master.updateVINStatus()

                            # Establish if this VIN should be able to charge
                            # If not, send stop command
                            master.queue_background_task(
                                {
                                    "cmd": "checkVINEntitlement",
                                    "subTWC": slaveTWC,
                                }
                            )

                            vinPart += 1
                        else:
                            # Unfortunately the VIN was not the right length.
                            # Re-request VIN
                            master.queue_background_task(
                                {
                                    "cmd": "getVehicleVIN",
                                    "slaveTWC": slaveTWC.TWCID,
                                    "vinPart": 0,
                                }
                            )

                    logger.log(
                        logging.INFO6,
                        "Current VIN string is: %s at part %d."
                        % (str(slaveTWC.VINData), vinPart),
                    )

                else:
                    msgMatch = re.search(
                        b"\A\xfc(\xe1|\xe2)(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00.+\Z",
                        msg,
                        re.DOTALL,
                    )
                if msgMatch and foundMsgMatch == False:
                    foundMsgMatch = True
                    logger.info(
                        "ERROR: TWC is set to Master mode so it can't be controlled by TWCManager.  "
                        "Search installation instruction PDF for 'rotary switch' and set "
                        "switch so its arrow points to F on the dial."
                    )
                if foundMsgMatch == False:
                    logger.info(
                        "*** UNKNOWN MESSAGE FROM SLAVE:"
                        + hex_str(msg)
                        + "\nPlease private message user CDragon at http://teslamotorsclub.com "
                        "with a copy of this error."
                    )
            else:
                ###########################
                # Pretend to be a slave TWC

                foundMsgMatch = False
                msgMatch = re.search(
                    b"\A\xfc\xe1(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00+?.\Z",
                    msg,
                    re.DOTALL,
                )
                if msgMatch and foundMsgMatch == False:
                    # Handle linkready1 from master.
                    # See notes in send_master_linkready1() for details.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    sign = msgMatch.group(2)
                    master.setMasterTWCID(senderID)

                    # This message seems to always contain seven 00 bytes in its
                    # data area. If we ever get this message with non-00 data
                    # we'll print it as an unexpected message.
                    logger.info(
                        "Master TWC %02X%02X Linkready1.  Sign: %s"
                        % (senderID[0], senderID[1], hex_str(sign))
                    )

                    if senderID == fakeTWCID:
                        master.master_id_conflict()

                    # Other than picking a new fakeTWCID if ours conflicts with
                    # master, it doesn't seem that a real slave will make any
                    # sort of direct response when sent a master's linkready1 or
                    # linkready2.

                else:
                    msgMatch = re.search(
                        b"\A\xfb\xe2(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00+?.\Z",
                        msg,
                        re.DOTALL,
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle linkready2 from master.
                    # See notes in send_master_linkready2() for details.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    sign = msgMatch.group(2)
                    master.setMasterTWCID(senderID)

                    # This message seems to always contain seven 00 bytes in its
                    # data area. If we ever get this message with non-00 data
                    # we'll print it as an unexpected message.

                    logger.info(
                        "Master TWC %02X%02X Linkready2.  Sign: %s"
                        % (senderID[0], senderID[1], hex_str(sign))
                    )

                    if senderID == fakeTWCID:
                        master.master_id_conflict()
                else:
                    msgMatch = re.search(
                        b"\A\xfb\xe0(..)(..)(.......+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle heartbeat message from Master.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    receiverID = msgMatch.group(2)
                    heartbeatData = msgMatch.group(3)
                    master.setMasterTWCID(senderID)
                    try:
                        slaveTWC = master.slaveTWCs[receiverID]
                    except KeyError:
                        slaveTWC = master.newSlave(receiverID, 80)

                    slaveTWC.masterHeartbeatData = heartbeatData

                    if receiverID != fakeTWCID:
                        # This message was intended for another slave.
                        # Ignore it.
                        logger.log(
                            logging.DEBUG2,
                            "Master %02X%02X sent "
                            "heartbeat message %s to receiver %02X%02X "
                            "that isn't our fake slave."
                            % (
                                senderID[0],
                                senderID[1],
                                hex_str(heartbeatData),
                                receiverID[0],
                                receiverID[1],
                            ),
                        )
                        continue

                    amps = (
                        master.slaveHeartbeatData[1] << 8
                    ) + master.slaveHeartbeatData[2]
                    master.addkWhDelivered(
                        (master.convertAmpsToWatts(amps / 100) / 1000 / 60 / 60)
                        * (now - timeLastkWhDelivered)
                    )
                    timeLastkWhDelivered = now
                    if time.time() - timeLastkWhSaved >= 300.0:
                        timeLastkWhSaved = now
                        logger.log(
                            logging.INFO9,
                            "Fake slave has delivered %.3fkWh"
                            % (master.getkWhDelivered()),
                        )
                        # Save settings to file
                        master.queue_background_task({"cmd": "saveSettings"})

                    if heartbeatData[0] == 0x07:
                        # Lower amps in use (not amps allowed) by 2 for 10
                        # seconds. Set state to 07.
                        master.slaveHeartbeatData[0] = heartbeatData[0]
                        timeToRaise2A = now + 10
                        amps -= 280
                        master.slaveHeartbeatData[3] = (amps >> 8) & 0xFF
                        master.slaveHeartbeatData[4] = amps & 0xFF
                    elif heartbeatData[0] == 0x06:
                        # Raise amp setpoint by 2 permanently and reply with
                        # state 06.  After 44 seconds, report state 0A.
                        timeTo0Aafter06 = now + 44
                        master.slaveHeartbeatData[0] = heartbeatData[0]
                        amps += 200
                        master.slaveHeartbeatData[1] = (amps >> 8) & 0xFF
                        master.slaveHeartbeatData[2] = amps & 0xFF
                        amps -= 80
                        master.slaveHeartbeatData[3] = (amps >> 8) & 0xFF
                        master.slaveHeartbeatData[4] = amps & 0xFF
                    elif (
                        heartbeatData[0] == 0x05
                        or heartbeatData[0] == 0x08
                        or heartbeatData[0] == 0x09
                    ):
                        if ((heartbeatData[1] << 8) + heartbeatData[2]) > 0:
                            # A real slave mimics master's status bytes [1]-[2]
                            # representing max charger power even if the master
                            # sends it a crazy value.
                            master.slaveHeartbeatData[1] = heartbeatData[1]
                            master.slaveHeartbeatData[2] = heartbeatData[2]

                            ampsUsed = (heartbeatData[1] << 8) + heartbeatData[2]
                            ampsUsed -= 80
                            master.slaveHeartbeatData[3] = (ampsUsed >> 8) & 0xFF
                            master.slaveHeartbeatData[4] = ampsUsed & 0xFF
                    elif heartbeatData[0] == 0:
                        if timeTo0Aafter06 > 0 and timeTo0Aafter06 < now:
                            timeTo0Aafter06 = 0
                            master.slaveHeartbeatData[0] = 0x0A
                        elif timeToRaise2A > 0 and timeToRaise2A < now:
                            # Real slave raises amps used by 2 exactly 10
                            # seconds after being sent into state 07. It raises
                            # a bit slowly and sets its state to 0A 13 seconds
                            # after state 07. We aren't exactly emulating that
                            # timing here but hopefully close enough.
                            timeToRaise2A = 0
                            amps -= 80
                            master.slaveHeartbeatData[3] = (amps >> 8) & 0xFF
                            master.slaveHeartbeatData[4] = amps & 0xFF
                            master.slaveHeartbeatData[0] = 0x0A
                    elif heartbeatData[0] == 0x02:
                        logger.info(
                            "Master heartbeat contains error %ld: %s"
                            % (heartbeatData[1], hex_str(heartbeatData))
                        )
                    else:
                        logger.info("UNKNOWN MHB state %s" % (hex_str(heartbeatData)))

                    # Slaves always respond to master's heartbeat by sending
                    # theirs back.
                    slaveTWC.send_slave_heartbeat(senderID)
                    slaveTWC.print_status(master.slaveHeartbeatData)
                else:
                    msgMatch = re.search(
                        b"\A\xfc\x1d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00+?.\Z",
                        msg,
                        re.DOTALL,
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle 2-hour idle message
                    #
                    # This message is sent from a Master TWC three times in a
                    # row every 2 hours:
                    #   c0 fc 1d 00 00 00 00 00 00 00 00 00 00 00 1d c0
                    #
                    # I'd say this is used to indicate the master is still
                    # alive, but it doesn't contain the Master's TWCID or any other
                    # data so I don't see what any receiving TWC can do with it.
                    #
                    # I suspect this message is only sent when the master
                    # doesn't see any other TWCs on the network, so I don't
                    # bother to have our fake master send these messages being
                    # as there's no point in playing a fake master with no
                    # slaves around.
                    foundMsgMatch = True
                    logger.info("Received 2-hour idle message from Master.")
                else:
                    msgMatch = re.search(
                        b"\A\xfd\xe2(..)(.)(..)\x00\x00\x00\x00\x00\x00.+\Z",
                        msg,
                        re.DOTALL,
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle linkready message from slave on network that
                    # presumably isn't us.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    sign = msgMatch.group(2)
                    maxAmps = ((msgMatch.group(3)[0] << 8) + msgMatch.group(3)[1]) / 100
                    logger.info(
                        "%.2f amp slave TWC %02X%02X is ready to link.  Sign: %s"
                        % (maxAmps, senderID[0], senderID[1], hex_str(sign))
                    )
                    if senderID == fakeTWCID:
                        logger.info(
                            "ERROR: Received slave heartbeat message from "
                            "slave %02X%02X that has the same TWCID as our fake slave."
                            % (senderID[0], senderID[1])
                        )
                        continue

                    master.newSlave(senderID, maxAmps)
                else:
                    msgMatch = re.search(
                        b"\A\xfd\xe0(..)(..)(.......+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle heartbeat message from slave on network that
                    # presumably isn't us.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    receiverID = msgMatch.group(2)
                    heartbeatData = msgMatch.group(3)

                    if senderID == fakeTWCID:
                        logger.info(
                            "ERROR: Received slave heartbeat message from "
                            "slave %02X%02X that has the same TWCID as our fake slave."
                            % (senderID[0], senderID[1])
                        )
                        continue

                    try:
                        slaveTWC = master.slaveTWCs[senderID]
                    except KeyError:
                        # Slave is unlikely to send another linkready since it's
                        # already linked with a real Master TWC, so just assume
                        # it's 80A.
                        slaveTWC = master.newSlave(senderID, 80)

                    slaveTWC.print_status(heartbeatData)
                else:
                    msgMatch = re.search(
                        b"\A\xfb\xeb(..)(..)(\x00\x00\x00\x00\x00\x00\x00\x00\x00+?).\Z",
                        msg,
                        re.DOTALL,
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle voltage request message.  This is only supported in
                    # Protocol 2 so we always reply with a 16-byte message.
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    receiverID = msgMatch.group(2)

                    if senderID == fakeTWCID:
                        logger.info(
                            "ERROR: Received voltage request message from "
                            "TWC %02X%02X that has the same TWCID as our fake slave."
                            % (senderID[0], senderID[1])
                        )
                        continue

                    logger.log(
                        logging.INFO8,
                        "VRQ from %02X%02X to %02X%02X"
                        % (senderID[0], senderID[1], receiverID[0], receiverID[1]),
                    )

                    if receiverID == fakeTWCID:
                        kWhCounter = int(master.getkWhDelivered())
                        kWhPacked = bytearray(
                            [
                                ((kWhCounter >> 24) & 0xFF),
                                ((kWhCounter >> 16) & 0xFF),
                                ((kWhCounter >> 8) & 0xFF),
                                (kWhCounter & 0xFF),
                            ]
                        )
                        logger.info(
                            "VRS %02X%02X: %dkWh (%s) %dV %dV %dV"
                            % (
                                fakeTWCID[0],
                                fakeTWCID[1],
                                kWhCounter,
                                hex_str(kWhPacked),
                                240,
                                0,
                                0,
                            )
                        )
                        master.getInterfaceModule().send(
                            bytearray(b"\xFD\xEB")
                            + fakeTWCID
                            + kWhPacked
                            + bytearray(b"\x00\xF0\x00\x00\x00\x00\x00")
                        )
                else:
                    msgMatch = re.search(
                        b"\A\xfd\xeb(..)(.........+?).\Z", msg, re.DOTALL
                    )
                if msgMatch and foundMsgMatch == False:
                    # Handle voltage response message.
                    # Example US value:
                    #   FD EB 7777 00000014 00F6 0000 0000 00
                    # EU value (3 phase power):
                    #   FD EB 7777 00000038 00E6 00F1 00E8 00
                    foundMsgMatch = True
                    senderID = msgMatch.group(1)
                    data = msgMatch.group(2)
                    kWhCounter = (
                        (data[0] << 24) + (data[1] << 16) + (data[2] << 8) + data[3]
                    )
                    voltsPhaseA = (data[4] << 8) + data[5]
                    voltsPhaseB = (data[6] << 8) + data[7]
                    voltsPhaseC = (data[8] << 8) + data[9]

                    # Update this detail for the Slave TWC
                    master.updateSlaveLifetime(
                        senderID, kWhCounter, voltsPhaseA, voltsPhaseB, voltsPhaseC
                    )

                    if senderID == fakeTWCID:
                        logger.info(
                            "ERROR: Received voltage response message from "
                            "TWC %02X%02X that has the same TWCID as our fake slave."
                            % (senderID[0], senderID[1])
                        )
                        continue

                    logger.info(
                        "VRS %02X%02X: %dkWh %dV %dV %dV"
                        % (
                            senderID[0],
                            senderID[1],
                            kWhCounter,
                            voltsPhaseA,
                            voltsPhaseB,
                            voltsPhaseC,
                        )
                    )

                if foundMsgMatch == False:
                    logger.info("***UNKNOWN MESSAGE from master: " + hex_str(msg))

    except KeyboardInterrupt:
        logger.info("Exiting after background tasks complete...")
        break

    except Exception as e:
        # Print info about unhandled exceptions, then continue.  Search for
        # 'Traceback' to find these in the log.
        traceback.print_exc()
        logger.info("Unhandled Exception:" + traceback.format_exc())
        # Sleep 5 seconds so the user might see the error.
        time.sleep(5)

# Make sure any volatile data is written to disk before exiting
master.queue_background_task({"cmd": "saveSettings"})

# Wait for background tasks thread to finish all tasks.
# Note that there is no such thing as backgroundTasksThread.stop(). Because we
# set the thread type to daemon, it will be automatically killed when we exit
# this program.
master.backgroundTasksQueue.join()

# Close the input module
master.getInterfaceModule().close()

#
# End main program
#
##############################
