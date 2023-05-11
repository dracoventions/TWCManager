import jinja2
import json
import logging
import math
import mimetypes
import os
import pathlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timedelta
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid

logger = logging.getLogger("\U0001F3AE HTTP")


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class HTTPControl:
    configConfig = {}
    configHTTP = {}
    httpPort = 8080
    master = None
    status = False

    def __init__(self, master):
        self.master = master
        try:
            self.configConfig = master.config["config"]
        except KeyError:
            self.configConfig = {}
        try:
            self.configHTTP = master.config["control"]["HTTP"]
        except KeyError:
            self.configHTTP = {}
        self.httpPort = self.configHTTP.get("listenPort", 8080)
        self.status = self.configHTTP.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (int(self.httpPort) < 1):
            self.master.releaseModule("lib.TWCManager.Control", self.__class__.__name__)
            return None

        HTTPHandler = CreateHTTPHandlerClass(master)
        httpd = None
        try:
            httpd = ThreadingSimpleServer(("", self.httpPort), HTTPHandler)
        except OSError as e:
            logger.error("Unable to start HTTP Server: " + str(e))

        if httpd:
            logger.info("Serving at port: " + str(self.httpPort))
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
        else:
            self.master.releaseModule("lib.TWCManager.Control", self.__class__.__name__)


def CreateHTTPHandlerClass(master):
    class HTTPControlHandler(BaseHTTPRequestHandler):
        ampsList = []
        fields = {}
        host = None
        hoursDurationList = []
        master = None
        path = ""
        post_data = ""
        templateEnv = None
        templateLoader = None
        timeList = []
        url = None

        def __init__(self, *args, **kwargs):
            # Populate ampsList so that any function which requires a list of supported
            # TWC amps can easily access it
            if not len(self.ampsList):
                self.ampsList.append([0, "Disabled"])
                for amp in range(
                    master.config["config"].get("minAmpsPerTWC", 5),
                    (
                        master.config["config"].get(
                            "wiringMaxAmpsPerTWC",
                            master.config["config"].get("minAmpsPerTWC", 5),
                        )
                    )
                    + 1,
                ):
                    self.ampsList.append([amp, str(amp) + "A"])

            # Populate list of hours
            if not len(self.hoursDurationList):
                for hour in range(1, 25):
                    self.hoursDurationList.append([(hour * 3600), str(hour) + "h"])

            if not len(self.timeList):
                for hour in range(0, 24):
                    for mins in [0, 15, 30, 45]:
                        strHour = str(hour)
                        strMins = str(mins)
                        if hour < 10:
                            strHour = "0" + str(hour)
                        if mins < 10:
                            strMins = "0" + str(mins)
                        self.timeList.append(
                            [strHour + ":" + strMins, strHour + ":" + strMins]
                        )

            # Define jinja2 template environment
            # Note that we specify two paths in order to the template loader.
            # The first is the user specified template. The second is the default.
            # Jinja2 will try for the specified template first, however if any files
            # are not found, it will fall back to the default theme.
            self.templateLoader = jinja2.FileSystemLoader(
                searchpath=[
                    pathlib.Path(__file__).resolve().parent.as_posix()
                    + "/themes/"
                    + master.settings.get("webControlTheme", "Modern")
                    + "/",
                    pathlib.Path(__file__).resolve().parent.as_posix()
                    + "/themes/Default/",
                ]
            )
            self.templateEnv = jinja2.Environment(
                loader=self.templateLoader, autoescape=True
            )

            # Make certain functions available to jinja2
            # Where we have helper functions that we've used in the fast to
            # render HTML, we can keep using those even inside jinja2
            self.templateEnv.globals.update(addButton=self.addButton)
            self.templateEnv.globals.update(ampsList=self.ampsList)
            self.templateEnv.globals.update(
                apiChallenge=master.getModuleByName("TeslaAPI").getApiChallenge
            )
            self.templateEnv.globals.update(chargeScheduleDay=self.chargeScheduleDay)
            self.templateEnv.globals.update(checkBox=self.checkBox)
            self.templateEnv.globals.update(checkForUpdates=master.checkForUpdates)
            self.templateEnv.globals.update(doChargeSchedule=self.do_chargeSchedule)
            self.templateEnv.globals.update(host=self.host)
            self.templateEnv.globals.update(hoursDurationList=self.hoursDurationList)
            self.templateEnv.globals.update(navbarItem=self.navbar_item)
            self.templateEnv.globals.update(optionList=self.optionList)
            self.templateEnv.globals.update(timeList=self.timeList)
            self.templateEnv.globals.update(
                vehicles=master.getModuleByName("TeslaAPI").getCarApiVehicles
            )

            # Set master object
            self.master = master

            # Call parent constructor last, this is where the request is served
            BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

        def checkBox(self, name, value):
            cb = "<input type=checkbox name='" + name + "'"
            if value:
                cb += " checked"
            cb += ">"
            return cb

        def do_chargeSchedule(self):
            schedule = [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ]
            settings = master.settings.get("Schedule", {})

            page = """
    <table class='table table-sm'>
      <thead>
        <th scope='col'>&nbsp;</th>
        """
            for day in schedule:
                page += "<th scope='col'>" + day[:3] + "</th>"
            page += """
      </thead>
      <tbody>"""
            for i in (x for y in (range(6, 24), range(0, 6)) for x in y):
                page += "<tr><th scope='row'>%02d</th>" % (i)
                for day in schedule:
                    today = settings.get(day, {})
                    curday = settings.get("Common", {})
                    if settings.get("schedulePerDay", 0):
                        curday = settings.get(day, {})
                    if (
                        today.get("enabled", None) == "on"
                        and (int(curday.get("start", 0)[:2]) <= int(i))
                        and (int(curday.get("end", 0)[:2]) >= int(i))
                    ):
                        page += (
                            "<td bgcolor='#CFFAFF'>SC @ "
                            + str(
                                settings.get("Settings", {}).get("scheduledAmpsMax", 0)
                            )
                            + "A</td>"
                        )
                    else:
                        # Todo - need to mark track green + non scheduled chg
                        page += "<td bgcolor='#FFDDFF'>&nbsp;</td>"
                page += "</tr>"
            page += "</tbody>"
            page += "</table>"

            return page

        def navbar_item(self, url, name, target="_self"):
            active = ""
            urlp = urllib.parse.urlparse(self.path)
            if urlp.path == url:
                active = "active"
            page = "<li class='nav-item %s'>" % active
            page += "<a class='nav-link' target='%s' href='%s'>%s</a>" % (
                target,
                url,
                name,
            )
            page += "</li>"
            return page

        def do_API_GET(self):
            self.debugLogAPI("Starting API GET")
            if self.url.path == "/api/getConfig":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(master.config)
                # Scrub output of passwords and API keys
                json_datas = re.sub(r'"password": ".*?",', "", json_data)
                json_data = re.sub(r'"apiKey": ".*?",', "", json_datas)
                self.wfile.write(json_data.encode("utf-8"))

            elif self.url.path == "/api/getConsumptionOffsets":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                if not master.settings.get("consumptionOffset", None):
                    master.settings["consumptionOffset"] = {}

                json_data = json.dumps(master.settings["consumptionOffset"])
                self.wfile.write(json_data.encode("utf-8"))

            elif self.url.path == "/api/getLastTWCResponse":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()

                self.wfile.write(str(master.lastTWCResponseMsg).encode("utf-8"))

            elif self.url.path == "/api/getPolicy":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(master.getModuleByName("Policy").charge_policy)
                self.wfile.write(json_data.encode("utf-8"))

            elif self.url.path == "/api/getSlaveTWCs":
                data = {}
                totals = {
                    "lastAmpsOffered": 0,
                    "lifetimekWh": 0,
                    "maxAmps": 0,
                    "reportedAmpsActual": 0,
                }
                for slaveTWC in master.getSlaveTWCs():
                    TWCID = "%02X%02X" % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
                    data[TWCID] = {
                        "currentVIN": slaveTWC.currentVIN,
                        "lastAmpsOffered": round(slaveTWC.lastAmpsOffered, 2),
                        "lastHeartbeat": round(time.time() - slaveTWC.timeLastRx, 2),
                        "carsCharging": slaveTWC.isCharging,
                        "lastVIN": slaveTWC.lastVIN,
                        "lifetimekWh": slaveTWC.lifetimekWh,
                        "maxAmps": float(slaveTWC.maxAmps),
                        "reportedAmpsActual": float(slaveTWC.reportedAmpsActual),
                        "chargerLoadInW": round(slaveTWC.getCurrentChargerLoad()),
                        "state": slaveTWC.reportedState,
                        "version": slaveTWC.protocolVersion,
                        "voltsPhaseA": slaveTWC.voltsPhaseA,
                        "voltsPhaseB": slaveTWC.voltsPhaseB,
                        "voltsPhaseC": slaveTWC.voltsPhaseC,
                        "TWCID": "%s" % TWCID,
                    }

                    if slaveTWC.lastChargingStart > 0:
                        data[TWCID]["chargeTime"] = str(
                            timedelta(
                                seconds=(time.time() - slaveTWC.lastChargingStart)
                            )
                        ).split(".")[0]
                    else:
                        data[TWCID]["chargeTime"] = "--:--:--"

                    # Adding some vehicle data
                    vehicle = slaveTWC.getLastVehicle()
                    if vehicle != None:
                        data[TWCID]["lastBatterySOC"] = vehicle.batteryLevel
                        data[TWCID]["lastChargeLimit"] = vehicle.chargeLimit
                        data[TWCID]["lastAtHome"] = vehicle.atHome
                        data[TWCID]["lastTimeToFullCharge"] = vehicle.timeToFullCharge

                    totals["lastAmpsOffered"] += slaveTWC.lastAmpsOffered
                    totals["lifetimekWh"] += slaveTWC.lifetimekWh
                    totals["maxAmps"] += slaveTWC.maxAmps
                    totals["reportedAmpsActual"] += slaveTWC.reportedAmpsActual

                data["total"] = {
                    "lastAmpsOffered": round(totals["lastAmpsOffered"], 2),
                    "lifetimekWh": totals["lifetimekWh"],
                    "maxAmps": totals["maxAmps"],
                    "reportedAmpsActual": round(totals["reportedAmpsActual"], 2),
                    "TWCID": "total",
                }

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(data)
                self.wfile.write(json_data.encode("utf-8"))

            elif self.url.path == "/api/getStatus":
                data = master.getStatus()
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(data)
                try:
                    self.wfile.write(json_data.encode("utf-8"))
                except BrokenPipeError:
                    self.debugLogAPI("Connection Error: Broken Pipe")

            elif self.url.path == "/api/getActivePolicyAction":
                data = master.getModuleByName("Policy").getActivePolicyAction()
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(data)
                try:
                    self.wfile.write(json_data.encode("utf-8"))
                except BrokenPipeError:
                    self.debugLogAPI("Connection Error: Broken Pipe")

            elif self.url.path == "/api/getHistory":
                output = []
                now = datetime.now().replace(second=0, microsecond=0).astimezone()
                startTime = now - timedelta(days=2) + timedelta(minutes=5)
                endTime = now.replace(minute=math.floor(now.minute / 5) * 5)
                startTime = startTime.replace(
                    minute=math.floor(startTime.minute / 5) * 5
                )

                source = (
                    master.settings["history"] if "history" in master.settings else []
                )
                data = {
                    k: v for k, v in source if datetime.fromisoformat(k) >= startTime
                }

                avgCurrent = 0
                for slave in master.getSlaveTWCs():
                    avgCurrent += slave.historyAvgAmps
                data[endTime.isoformat(timespec="seconds")] = master.convertAmpsToWatts(
                    avgCurrent
                )

                output = [
                    {
                        "timestamp": timestamp,
                        "charger_power": data[timestamp] if timestamp in data else 0,
                    }
                    for timestamp in [
                        (startTime + timedelta(minutes=5 * i)).isoformat(
                            timespec="seconds"
                        )
                        for i in range(48 * 12)
                    ]
                ]

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                json_data = json.dumps(output)
                self.wfile.write(json_data.encode("utf-8"))

            elif self.url.path == "/api/getUUID":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()

                self.wfile.write(str(uuid.getnode()).encode("utf-8"))

            else:
                # All other routes missed, return 404
                self.send_response(404)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            self.debugLogAPI("Ending API GET")

        def do_API_POST(self):
            self.debugLogAPI("Starting API POST")

            if self.url.path == "/api/addConsumptionOffset":
                data = {}
                try:
                    data = json.loads(self.post_data.decode("UTF-8"))
                except (ValueError, UnicodeDecodeError):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))
                except json.decoder.JSONDecodeError:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))
                name = str(data.get("offsetName", None))
                value = float(data.get("offsetValue", 0))
                unit = str(data.get("offsetUnit", ""))

                if (
                    name
                    and value
                    and (unit == "A" or unit == "W")
                    and len(name) < 32
                    and not self.checkForUnsafeCharactters(name)
                ):
                    if not master.settings.get("consumptionOffset", None):
                        master.settings["consumptionOffset"] = {}
                    master.settings["consumptionOffset"][name] = {}
                    master.settings["consumptionOffset"][name]["value"] = value
                    master.settings["consumptionOffset"][name]["unit"] = unit
                    master.queue_background_task({"cmd": "saveSettings"})

                    self.send_response(204)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/chargeNow":
                data = {}
                try:
                    data = json.loads(self.post_data.decode("UTF-8"))
                except (ValueError, UnicodeDecodeError):
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))
                except json.decoder.JSONDecodeError:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))
                rate = int(data.get("chargeNowRate", 0))
                durn = int(data.get("chargeNowDuration", 0))

                if rate <= 0 or durn <= 0:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

                else:
                    master.setChargeNowAmps(rate)
                    master.setChargeNowTimeEnd(durn)
                    master.queue_background_task({"cmd": "saveSettings"})
                    master.getModuleByName("Policy").applyPolicyImmediately()
                    self.send_response(204)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/cancelChargeNow":
                master.resetChargeNowAmps()
                master.queue_background_task({"cmd": "saveSettings"})
                master.getModuleByName("Policy").applyPolicyImmediately()
                self.send_response(204)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/checkArrival":
                master.queue_background_task({"cmd": "checkArrival"})
                self.send_response(202)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/checkDeparture":
                master.queue_background_task({"cmd": "checkDeparture"})
                self.send_response(202)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/deleteConsumptionOffset":
                data = json.loads(self.post_data.decode("UTF-8"))
                name = str(data.get("offsetName", None))

                if master.settings.get("consumptionOffset", None):
                    del master.settings["consumptionOffset"][name]

                    self.send_response(204)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write("".encode("utf-8"))

            elif self.url.path == "/api/saveSettings":
                master.queue_background_task({"cmd": "saveSettings"})
                self.send_response(204)
                self.end_headers()

            elif self.url.path == "/api/sendDebugCommand":
                data = json.loads(self.post_data.decode("UTF-8"))
                packet = {"Command": data.get("commandName", "")}
                if data.get("commandName", "") == "Custom":
                    packet["CustomCommand"] = data.get("customCommand", "")

                # Clear last TWC response, so we can grab the next response
                master.lastTWCResponseMsg = bytearray()

                # Send packet to network
                master.getModuleByName("RS485").send(
                    master.getModuleByName("TWCProtocol").createMessage(packet)
                )

                self.send_response(204)
                self.end_headers()

            elif self.url.path == "/api/sendStartCommand":
                master.sendStartCommand()
                self.send_response(204)
                self.end_headers()

            elif self.url.path == "/api/sendStopCommand":
                master.sendStopCommand()
                self.send_response(204)
                self.end_headers()

            elif self.url.path == "/api/sendTeslaAPICommand":
                data = json.loads(self.post_data.decode("UTF-8"))
                command = str(data.get("commandName", None))
                vehicle = str(data.get("vehicleID", None))
                params = str(data.get("parameters", None))

                res = master.getModuleByName("TeslaAPI").apiDebugInterface(
                    command, vehicle, params
                )
                if res == True:
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.end_headers()

            elif self.url.path == "/api/setSetting":
                data = json.loads(self.post_data.decode("UTF-8"))
                setting = str(data.get("setting", None))
                value = str(data.get("value", None))

                if (
                    setting
                    and value
                    and not self.checkForUnsafeCharactters(setting)
                    and not self.checkForUnsafeCharactters(value)
                ):
                    master.settings[setting] = value
                self.send_response(204)
                self.end_headers()

            elif self.url.path == "/api/setScheduledChargingSettings":
                data = json.loads(self.post_data.decode("UTF-8"))
                enabled = bool(data.get("enabled", False))
                startingMinute = int(data.get("startingMinute", -1))
                endingMinute = int(data.get("endingMinute", -1))
                monday = bool(data.get("monday", False))
                tuesday = bool(data.get("tuesday", False))
                wednesday = bool(data.get("wednesday", False))
                thursday = bool(data.get("thursday", False))
                friday = bool(data.get("friday", False))
                saturday = bool(data.get("saturday", False))
                sunday = bool(data.get("sunday", False))
                amps = int(data.get("amps", -1))
                batterySize = int(
                    data.get("flexBatterySize", 100)
                )  # using 100 as default, because with this every available car at moment should be finished with charging at the ending time
                flexStart = int(data.get("flexStartEnabled", False))
                weekDaysBitmap = (
                    (1 if monday else 0)
                    + (2 if tuesday else 0)
                    + (4 if wednesday else 0)
                    + (8 if thursday else 0)
                    + (16 if friday else 0)
                    + (32 if saturday else 0)
                    + (64 if sunday else 0)
                )

                if (
                    not (enabled)
                    or startingMinute < 0
                    or endingMinute < 0
                    or amps <= 0
                    or weekDaysBitmap == 0
                ):
                    master.setScheduledAmpsMax(0)
                    master.setScheduledAmpsStartHour(-1)
                    master.setScheduledAmpsEndHour(-1)
                    master.setScheduledAmpsDaysBitmap(0)
                else:
                    master.setScheduledAmpsMax(amps)
                    master.setScheduledAmpsStartHour(startingMinute / 60)
                    master.setScheduledAmpsEndHour(endingMinute / 60)
                    master.setScheduledAmpsDaysBitmap(weekDaysBitmap)
                master.setScheduledAmpsBatterySize(batterySize)
                master.setScheduledAmpsFlexStart(flexStart)
                master.queue_background_task({"cmd": "saveSettings"})
                self.send_response(202)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            else:
                # All other routes missed, return 404
                self.send_response(404)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))

            self.debugLogAPI("Ending API POST")

        def do_get_policy(self):
            page = """
      <table>
        """
            j = 0
            mod_policy = master.getModuleByName("Policy")
            insertion_points = {0: "Emergency", 1: "Before", 3: "After"}
            replaced = all(
                x not in mod_policy.default_policy for x in mod_policy.charge_policy
            )
            for policy in mod_policy.charge_policy:
                if policy in mod_policy.default_policy:
                    cat = "Default"
                    ext = insertion_points.get(j, None)

                    if ext:
                        page += "<tr><th>Policy Extension Point</th></tr>"
                        page += "<tr><td>" + ext + "</td></tr>"

                    j += 1
                else:
                    cat = "Custom" if replaced else insertion_points.get(j, "Unknown")
                page += (
                    "<tr><td>&nbsp;</td><td>"
                    + policy["name"]
                    + " ("
                    + cat
                    + ")</td></tr>"
                )
                page += "<tr><th>&nbsp;</th><th>&nbsp;</th><th>Match Criteria</th><th>Condition</th><th>Value</th></tr>"
                for match, condition, value in zip(
                    policy["match"], policy["condition"], policy["value"]
                ):
                    page += "<tr><td>&nbsp;</td><td>&nbsp;</td>"
                    page += "<td>" + str(match)
                    match_result = mod_policy.policyValue(match)
                    if match != match_result:
                        page += " (" + str(match_result) + ")"
                    page += "</td>"

                    page += "<td>" + str(condition) + "</td>"

                    page += "<td>" + str(value)
                    value_result = mod_policy.policyValue(value)
                    if value != value_result:
                        page += " (" + str(value_result) + ")"
                    page += "</td></tr>"

            page += """
      </table>
      </div>
    </body>
        """
            return page

        def do_GET(self):
            self.url = urllib.parse.urlparse(self.path)

            # Determine host header entry
            try:
                self.host = self.headers.get("Host", "")

                # Remove port number from domain
                if ":" in self.host:
                    self.host = self.host.split(":", 1)[0]
            except IndexError:
                self.host = None

            # serve local static content files (from './lib/TWCManager/Control/static/' dir)
            if self.url.path.startswith("/static/"):
                content_type = mimetypes.guess_type(self.url.path)[0]

                # only server know content type
                if content_type is not None:
                    filename = (
                        pathlib.Path(__file__).resolve().parent.as_posix()
                        + self.url.path
                    )

                    # check if static file exists and is readable
                    if os.path.isfile(filename) and os.access(filename, os.R_OK):
                        self.send_response(200)
                        self.send_header("Content-type", content_type)
                        self.end_headers()

                        # send static content (e.g. images) to browser
                        with open(filename, "rb") as staticFile:
                            self.wfile.write(staticFile.read())
                            return
                    else:
                        # static file doesn't exit or isn't readable
                        self.send_response(404)
                        return

            # Service API requests
            if self.url.path.startswith("/api/"):
                self.do_API_GET()
                return

            webroutes = [
                {"route": "/debug", "tmpl": "debug.html.j2"},
                {"route": "/schedule", "tmpl": "schedule.html.j2"},
                {"route": "/settings", "tmpl": "settings.html.j2"},
                {"route": "/settings/homeLocation", "error": "insecure"},
                {"route": "/settings/save", "error": "insecure"},
                {"route": "/teslaAccount/saveToken", "error": "insecure"},
                {"rstart": "/teslaAccount", "tmpl": "main.html.j2"},
                {"route": "/upgradePrompt", "tmpl": "upgradePrompt.html.j2"},
                {"rstart": "/vehicleDetail", "tmpl": "vehicleDetail.html.j2"},
                {"route": "/vehicles", "tmpl": "vehicles.html.j2"},
            ]

            if self.url.path == "/":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # Load "main" template and render
                self.template = self.templateEnv.get_template("main.html.j2")

                # Set some values that we use within the template
                # Check if we're able to access the Tesla API
                self.apiAvailable = master.getModuleByName(
                    "TeslaAPI"
                ).car_api_available()
                self.scheduledAmpsMax = master.getScheduledAmpsMax()

                self.activeAction = master.getModuleByName(
                    "Policy"
                ).getActivePolicyAction()

                # Send the html message
                page = self.template.render(vars(self))

                self.wfile.write(page.encode("utf-8"))
                return

            # Match web routes to defined webroutes routing
            route = None
            for webroute in webroutes:
                if self.url.path == webroute.get("route", "INVALID"):
                    route = webroute
                    break
                elif self.url.path.startswith(webroute.get("rstart", "INVALID")):
                    route = webroute
                    break

            if route and route.get("error", None):
                if route["error"] == "insecure":
                    # For security, these details should be submitted via a POST request
                    # Send a 405 Method Not Allowed in response.
                    self.send_response(405)
                    page = (
                        "This function may only be requested via the POST HTTP method."
                    )
                    self.wfile.write(page.encode("utf-8"))
                    return

                else:
                    self.send_response(500)
                    self.wfile.write("".encode("utf-8"))
                    return

            elif route:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # Load debug template and render
                self.template = self.templateEnv.get_template(route["tmpl"])
                page = self.template.render(self.__dict__)

                self.wfile.write(page.encode("utf-8"))
                return

            if self.url.path == "/policy":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                # Load policy template and render
                self.template = self.templateEnv.get_template("policy.html.j2")
                page = self.template.render(self.__dict__)

                page += self.do_get_policy()
                self.wfile.write(page.encode("utf-8"))
                return

            if self.url.path == "/upgrade":
                # This is extremely beta
                # Attempt a self-update of TWCManager by calling pip
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                self.template = self.templateEnv.get_template("upgrade.html.j2")
                page = self.template.render(self.__dict__)

                try:
                    page += subprocess.check_output(
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            "--user",
                            "--upgrade",
                            "TWCManager",
                        ]
                    ).decode("UTF-8")
                except subprocess.CalledProcessError as error:
                    page += "An error occurred attempting upgrade: " + str(error)

                self.wfile.write(page.encode("utf-8"))
                return

            if self.url.path.startswith("/vehicles/deleteGroup"):
                group = urllib.parse.unquote(self.url.path.rsplit("/", 1)[1])
                if (
                    group
                    and len(group) > 0
                    and group in master.settings["VehicleGroups"]
                ):
                    del master.settings["VehicleGroups"][group]
                    master.queue_background_task({"cmd": "saveSettings"})
                    self.send_response(302)
                    self.send_header("Location", "/vehicles")

                else:
                    self.send_response(400)

                self.end_headers()
                self.wfile.write("".encode("utf-8"))
                return

            if self.url.path == "/graphs" or self.url.path == "/graphsP":
                # We query the last 24h by default
                now = datetime.now().replace(second=0, microsecond=0)
                initial = now - timedelta(hours=24)
                end = now
                # It we came from a POST the dates should be already stored in settings
                if self.url.path == "/graphs":
                    self.process_save_graphs(
                        str(initial.strftime("%Y-%m-%dT%H:%M")),
                        str(end.strftime("%Y-%m-%dT%H:%M")),
                    )

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                # Load debug template and render
                self.template = self.templateEnv.get_template("graphs.html.j2")
                page = self.template.render(self.__dict__)
                self.wfile.write(page.encode("utf-8"))
                return

            if self.url.path == "/graphs/date":
                inicio = master.settings["Graphs"]["Initial"]
                fin = master.settings["Graphs"]["End"]

                self.process_graphs(inicio, fin)
                return

            # All other routes missed, return 404
            self.send_response(404)

        def do_POST(self):
            # Parse URL
            self.url = urllib.parse.urlparse(self.path)

            # Parse POST parameters
            self.fields.clear()
            length = int(self.headers.get("content-length"))
            self.post_data = self.rfile.read(length)

            if self.url.path.startswith("/api/"):
                self.do_API_POST()
                return

            self.fields = urllib.parse.parse_qs(self.post_data.decode("utf-8"))

            if self.url.path == "/debug/save":
                self.process_save_settings("debug")
                return

            if self.url.path == "/debug/saveToggle":
                self.process_save_settings("debug_toggle")
                return

            if self.url.path == "/schedule/save":
                # User has submitted schedule.
                self.process_save_schedule()
                return

            if self.url.path == "/settings/homeLocation":
                # User making changes to home location
                self.process_home_location()
                return

            if self.url.path == "/settings/save":
                # User has submitted settings.
                # Call dedicated function
                self.process_save_settings()
                return

            if self.url.path == "/graphs/dates":
                # User has submitted dates to graph this period.
                objIni = self.getFieldValue("dateIni")
                objEnd = self.getFieldValue("dateEnd")

                if not objIni or not objEnd:
                    # Redirect back to graphs page if no Start or End time supplied
                    self.send_response(302)
                    self.send_header("Location", "/graphs")

                else:
                    self.process_save_graphs(objIni, objEnd)
                    self.send_response(302)
                    self.send_header("Location", "/graphsP")

                self.end_headers()
                self.wfile.write("".encode("utf-8"))
                return

            if self.url.path == "/teslaAccount/saveToken":
                # Check if we are skipping Tesla Login submission
                later = False
                try:
                    later = len(self.fields["later"][0])
                except KeyError:
                    later = False

                res = ""
                url = self.getFieldValue("url")

                if later:
                    master.teslaLoginAskLater = True
                    res = "later"

                else:
                    res = master.getModuleByName("TeslaAPI").saveApiToken(url)

                self.send_response(302)
                self.send_header("Location", "/teslaAccount/" + res)

                self.end_headers()
                self.wfile.write("".encode("utf-8"))
                return

            if self.url.path == "/vehicle/groupMgmt":
                group = self.getFieldValue("group")
                op = self.getFieldValue("operation")
                vin = self.getFieldValue("vin")

                if op == "add":
                    try:
                        master.settings["VehicleGroups"][group]["Members"].append(vin)
                    except ValueError:
                        logger.error(
                            "Error adding vehicle %s to group %s" % (vin, group)
                        )

                elif op == "remove":
                    try:
                        master.settings["VehicleGroups"][group]["Members"].remove(vin)
                    except ValueError:
                        logger.error(
                            "Error removing vehicle %s from group %s" % (vin, group)
                        )

                master.queue_background_task({"cmd": "saveSettings"})

                master.queue_background_task(
                    {
                        "cmd": "checkVINEntitlement",
                        "vin": vin,
                    }
                )

                self.send_response(302)
                self.send_header("Location", "/vehicleDetail/" + vin)
                self.end_headers()
                self.wfile.write("".encode("utf-8"))
                return

            # All other routes missed, return 404
            self.send_response(404)
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return

        def addButton(self, button_def, extrargs):
            # This is a macro which can display differing buttons based on a
            # condition. It's a useful way to switch the text on a button based
            # on current state.
            params = {}
            if len(button_def) == 3:
                params = button_def[2]
            buttontype = "Submit"
            if params.get("buttonType", False):
                buttontype = params["buttonType"]
            page = "<input type='%s' %s id='%s' value='%s'>" % (
                buttontype,
                extrargs,
                button_def[0],
                button_def[1],
            )
            return page

        def chargeScheduleDay(self, day):
            # Fetch current settings
            sched = master.settings.get("Schedule", {})
            today = sched.get(day, {})
            suffix = day + "ChargeTime"

            # Render daily schedule options
            page = "<tr>"
            page += (
                "<td>"
                + self.checkBox("enabled" + suffix, today.get("enabled", 0))
                + "</td>"
            )
            page += "<td>" + str(day) + "</td>"
            page += (
                "<td>"
                + self.optionList(
                    self.timeList,
                    {"name": "start" + suffix, "value": today.get("start", "00:00")},
                )
                + "</td>"
            )
            page += "<td> to </td>"
            page += (
                "<td>"
                + self.optionList(
                    self.timeList,
                    {"name": "end" + suffix, "value": today.get("end", "00:00")},
                )
                + "</td>"
            )
            page += (
                "<td>" + self.checkBox("flex" + suffix, today.get("flex", 0)) + "</td>"
            )
            page += "<td>Flex Charge</td>"
            page += "</tr>"
            return page

        def checkForUnsafeCharactters(self, text):
            # Detect some unsafe characters in user input
            # The intention is to minimize the risk of either user input going into the settings file
            # or a database without pre-sanitization. We'll reject strings with these characters in them.
            unsafe_characters = '@#$%^&*"+<>;/'
            if any(c in unsafe_characters for c in text):
                return True
            else:
                return False

        def getFieldValue(self, key):
            # Parse the form value represented by key, and return the
            # value either as an integer or string
            keya = str(key)
            try:
                vala = self.fields[key][0].replace("'", "")
            except KeyError:
                return None
            try:
                if int(vala) or vala == "0":
                    return int(vala)
            except ValueError:
                return vala

        def log_message(self, format, *args):
            pass

        def optionList(self, list, opts={}):
            page = "<div class='form-group'>"
            page += "<select class='form-control' id='%s' name='%s'>" % (
                opts.get("name", ""),
                opts.get("name", ""),
            )
            for option in list:
                sel = ""
                if str(opts.get("value", "-1")) == str(option[0]):
                    sel = "selected"
                page += "<option value='%s' %s>%s</option>" % (
                    option[0],
                    sel,
                    option[1],
                )
            page += "</select>"
            page += "</div>"
            return page

        def process_home_location(self):
            # If unset was selected, unset account
            if "unset" in self.fields:
                del master.settings["homeLat"]
                del master.settings["homeLon"]

            # If learn was selected, learn location
            if "learn" in self.fields:
                loc = self.getFieldValue("vehicle").split(",")
                master.setHomeLon(loc[0])
                master.setHomeLat(loc[1])

            # Save Settings
            master.queue_background_task({"cmd": "saveSettings"})

            # Redirect to the index page
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return

        def process_save_schedule(self):
            # Check that schedule dict exists within settings.
            # If not, this would indicate that this is the first time
            # we have saved the new schedule settings
            if master.settings.get("Schedule", None) == None:
                master.settings["Schedule"] = {}

            # Slight issue with checkboxes, you have to default them all to
            # false, otherwise if one is unticked it is just not sent via form data
            days = [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ]
            for day in days:
                if master.settings["Schedule"].get(day, None) == None:
                    master.settings["Schedule"][day] = {}
                master.settings["Schedule"][day]["enabled"] = ""
                master.settings["Schedule"][day]["flex"] = ""

            # Detect schedule keys. Rather than saving them in a flat
            # structure, we'll store them multi-dimensionally
            fieldsout = self.fields.copy()
            ct = re.compile(
                r"(?P<trigger>enabled|end|flex|start)(?P<day>.*?)ChargeTime"
            )
            for key in self.fields:
                match = ct.match(key)
                if match:
                    # Detected a multi-dimensional (per-day) key
                    # Rewrite it into the settings array and delete it
                    # from the input

                    if master.settings["Schedule"].get(match.group(2), None) == None:
                        # Create dictionary key for this day
                        master.settings["Schedule"][match.group(2)] = {}

                    # Set per-day settings
                    master.settings["Schedule"][match.group(2)][
                        match.group(1)
                    ] = self.getFieldValue(key)

                else:
                    if master.settings["Schedule"].get("Settings", None) == None:
                        master.settings["Schedule"]["Settings"] = {}
                    master.settings["Schedule"]["Settings"][key] = self.getFieldValue(
                        key
                    )

            # During Phase 1 (backwards compatibility) for the new scheduling
            # UI, after writing the settings in the inteded new format, we then
            # write back to the existing settings nodes so that it is backwards
            # compatible.

            # Green Energy Tracking
            master.settings["hourResumeTrackGreenEnergy"] = int(
                master.settings["Schedule"]["Settings"]["resumeGreenEnergy"][:2]
            )

            # Scheduled amps
            master.settings["scheduledAmpsStartHour"] = int(
                master.settings["Schedule"]["Common"]["start"][:2]
            )
            master.settings["scheduledAmpsEndHour"] = int(
                master.settings["Schedule"]["Common"]["end"][:2]
            )
            master.settings["scheduledAmpsMax"] = float(
                master.settings["Schedule"]["Settings"]["scheduledAmpsMax"]
            )

            # Scheduled Days bitmap backward compatibility
            master.settings["scheduledAmpsDaysBitmap"] = (
                (1 if master.settings["Schedule"]["Monday"]["enabled"] else 0)
                + (2 if master.settings["Schedule"]["Tuesday"]["enabled"] else 0)
                + (4 if master.settings["Schedule"]["Wednesday"]["enabled"] else 0)
                + (8 if master.settings["Schedule"]["Thursday"]["enabled"] else 0)
                + (16 if master.settings["Schedule"]["Friday"]["enabled"] else 0)
                + (32 if master.settings["Schedule"]["Saturday"]["enabled"] else 0)
                + (64 if master.settings["Schedule"]["Sunday"]["enabled"] else 0)
            )

            # Save Settings
            master.queue_background_task({"cmd": "saveSettings"})

            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return

        def process_save_settings(self, page="settings"):
            # This function will write the settings submitted from the settings
            # page to the settings dict, before triggering a write of the settings
            # to file
            for key in self.fields:
                # If the key relates to the car API tokens, we need to pass these
                # to the appropriate module, rather than directly updating the
                # configuration file (as it would just be overwritten)
                if (
                    key == "carApiBearerToken" or key == "carApiRefreshToken"
                ) and self.getFieldValue(key) != "":
                    carapi = master.getModuleByName("TeslaAPI")
                    if key == "carApiBearerToken":
                        carapi.setCarApiBearerToken(self.getFieldValue(key))
                        # New tokens expire after 8 hours
                        carapi.setCarApiTokenExpireTime(time.time() + 8 * 60 * 60)
                    elif key == "carApiRefreshToken":
                        carapi.setCarApiRefreshToken(self.getFieldValue(key))
                        carapi.setCarApiTokenExpireTime(time.time() + 45 * 24 * 60 * 60)

                else:
                    # Write setting to dictionary
                    master.settings[key] = self.getFieldValue(key)

            # If Non-Scheduled power action is either Do not Charge or
            # Track Green Energy, set Non-Scheduled power rate to 0
            if int(master.settings.get("nonScheduledAction", 1)) > 1:
                master.settings["nonScheduledAmpsMax"] = 0

            # If triggered from the Debug page (not settings page), we need to
            # set certain settings to false if they were not seen in the
            # request data - This is because Check Boxes don't have a value
            # if they aren't set
            if page == "debug_toggle":
                if "enableDebugCommands" not in self.fields:
                    master.settings["enableDebugCommands"] = 0

            if page == "debug":
                checkboxes = [
                    "spikeAmpsProactively",
                    "spikeAmpsReactively",
                ]
                for checkbox in checkboxes:
                    if checkbox not in self.fields:
                        master.settings[checkbox] = 0

            # Save Settings
            master.queue_background_task({"cmd": "saveSettings"})

            # Redirect to the index page
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return

        def process_save_graphs(self, initial, end):
            # Check that Graphs dict exists within settings.
            # If not, this would indicate that this is the first time
            # we have saved it
            if master.settings.get("Graphs", None) == None:
                master.settings["Graphs"] = {}
            master.settings["Graphs"]["Initial"] = initial
            master.settings["Graphs"]["End"] = end

            return

        def process_graphs(self, init, end):
            # This function will query the green_energy SQL table
            result = {}

            # We will use the first loaded logging module with query capabilities to build the graphs.
            module = None

            for candidate_module in master.getModulesByType("Logging"):
                if candidate_module["ref"].getCapabilities("queryGreenEnergy"):
                    logger.log(
                        logging.INFO6,
                        "Logging module %s supports queryGreenEnergy",
                        candidate_module["name"],
                    )
                    module = candidate_module["ref"]
                else:
                    logger.log(
                        logging.INFO6,
                        "Logging module %s does not support queryGreenEnergy",
                        candidate_module["name"],
                    )

            # If we were unable to find a loaded Logging module with the capability to query
            # values for graphs, return a HTTP error code
            if not module:
                self.send_response(400)
                self.end_headers()
                return

            try:
                result = module.queryGreenEnergy(
                    {
                        "dateBegin": datetime.strptime(init, "%Y-%m-%dT%H:%M"),
                        "dateEnd": datetime.strptime(end, "%Y-%m-%dT%H:%M"),
                    }
                )
            except Exception as e:
                logger.exception("Excepcion queryGreenEnergy:")

            data = {}
            data[0] = {"initial": init, "end": end}
            i = 1
            while i < len(result):
                data[i] = {
                    "time": result[i][0].strftime("%Y-%m-%dT%H:%M:%S"),
                    "genW": str(result[i][1]),
                    "conW": str(result[i][2]),
                    "chgW": str(result[i][3]),
                }
                i = i + 1

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(data)
            try:
                self.wfile.write(json_data.encode("utf-8"))
            except BrokenPipeError:
                logger.debug("Connection Error: Broken Pipe")
            return

        def debugLogAPI(self, message):
            logger.debug(
                message
                + " (Url: "
                + str(self.url.path)
                + " / IP: "
                + str(self.client_address[0])
                + ")"
            )

    return HTTPControlHandler
