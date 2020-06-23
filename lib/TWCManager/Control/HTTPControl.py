from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from termcolor import colored
from datetime import datetime, timedelta
import json
import re
import threading
import time
import urllib.parse
import math
from ww import f


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class HTTPControl:

    configConfig = {}
    configHTTP = {}
    debugLevel = 1
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
        self.debugLevel = self.configConfig.get("debugLevel", 1)
        self.httpPort = self.configHTTP.get("listenPort", 8080)
        self.status = self.configHTTP.get("enabled", False)

        # Unload if this module is disabled or misconfigured
        if (not self.status) or (int(self.httpPort) < 1):
            self.master.releaseModule("lib.TWCManager.Control", "HTTPControl")

        if self.status:
            httpd = ThreadingSimpleServer(("", self.httpPort), HTTPControlHandler)
            httpd.master = master
            self.master.debugLog(
                1, "HTTPCtrl  ", "Serving at port: " + str(self.httpPort)
            )
            threading.Thread(target=httpd.serve_forever, daemon=True).start()


class HTTPControlHandler(BaseHTTPRequestHandler):

    fields = {}
    path = ""
    post_data = ""
    version = "v1.2.0"

    def do_bootstrap(self):
        page = """
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <script src="https://code.jquery.com/jquery-3.3.1.min.js" integrity="sha384-tsQFqpEReu7ZLhBV2VZlAu7zcOV+rXbYlF2cqB8txI/8aZajjp4Bqd+V6D5IgvKT" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
        <link rel='stylesheet' href='https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css' integrity='sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T' crossorigin='anonymous'>
        """
        return page

    def do_css(self):

        page = """
          <style>
          </style>
        """
        return page

    def do_chargeSchedule(self):
        page = """
    <table class='table table-sm'>
      <thead>
        <th scope='col'>&nbsp;</th>
        <th scope='col'>Sun</th>
        <th scope='col'>Mon</th>
        <th scope='col'>Tue</th>
        <th scope='col'>Wed</th>
        <th scope='col'>Thu</th>
        <th scope='col'>Fri</th>
        <th scope='col'>Sat</th>
      </thead>
      <tbody>"""
        for i in (x for y in (range(6, 24), range(0, 6)) for x in y):
            page += "<tr><th scope='row'>%02d</th>" % (i)
            for day in range(0, 6):
                page += "<td>&nbsp;</td>"
            page += "</tr>"
        page += "</tbody>"
        page += "</table>"

        return page

    def do_jsrefresh(self):
        page = """
      <script language = 'JavaScript'>

      // AJAJ refresh for getStatus API call
      $(document).ready(function() {  
          function requestStatus() {
              $.ajax({
                  url: "/api/getStatus",
                  dataType: "text",
                  cache: false,
                  success: function(data) {
                      var json = $.parseJSON(data);
                      Object.keys(json).forEach(function(key) {
                        $('#'+key).html(json[key]);
                      });

                      // Change the state of the Charge Now button based on Charge Policy
                      if (json["currentPolicy"] == "Charge Now") {
                        document.getElementById("start_chargenow").value = "Update Charge Now";
                        document.getElementById("cancel_chargenow").disabled = false;
                      } else {
                        document.getElementById("start_chargenow").value = "Start Charge Now";
                        document.getElementById("cancel_chargenow").disabled = true;
                      }
                  }             
              });
              setTimeout(requestStatus, 3000);
          }

          requestStatus();
      });

      // AJAJ refresh for getSlaveTWCs API call
      $(document).ready(function() {
          function requestSlaves() {
              $.ajax({
                  url: "/api/getSlaveTWCs",
                  dataType: "text",
                  cache: false,
                  success: function(data) {
                      var json = $.parseJSON(data);
                      Object.keys(json).forEach(function(key) {
                        var slvtwc = json[key];
                        var twc = '#' + slvtwc['TWCID']
                        Object.keys(slvtwc).forEach(function(key) {
                          $(twc+'_'+key).html(slvtwc[key]);
                        });
                      });
                  }
              });
              setTimeout(requestSlaves, 3000);
          }

          requestSlaves();
      });

      $(document).ready(function() {
        $("#start_chargenow").click(function(e) {
          e.preventDefault();
          $.ajax({
            type: "POST",
            url: "/api/chargeNow",
            data: JSON.stringify({
              chargeNowRate: $("#chargeNowRate").val(),
              chargeNowDuration: $("#chargeNowDuration").val()
            }),
            dataType: "json"
          });
        });
      });

      $(document).ready(function() {
        $("#cancel_chargenow").click(function(e) {
          e.preventDefault();
          $.ajax({
            type: "POST",
            url: "/api/cancelChargeNow",
            data: {}
          });
        });
      });

      $(document).ready(function() {
        $("#send_start_command").click(function(e) {
          e.preventDefault();
          $.ajax({
            type: "POST",
            url: "/api/sendStartCommand",
            data: {}
          });
        });
      });

      $(document).ready(function() {
        $("#send_stop_command").click(function(e) {
          e.preventDefault();
          $.ajax({
            type: "POST",
            url: "/api/sendStopCommand",
            data: {}
          });
        });
      });

      // Enable tooltips
      $(function () {
        $('[data-toggle="tooltip"]').tooltip()
      })
      </script> """
        return page

    def do_navbar(self):
        page = """
    <p>&nbsp;</p>
    <p>&nbsp;</p>
    <nav class='navbar fixed-top navbar-dark bg-dark' role='navigation'>
      <a class='navbar-brand' href='/'>TWCManager</a>
        """
        page += (
            "<link rel='icon' type='image/png' href='https://raw.githubusercontent.com/ngardiner/TWCManager/master/tree/%s/html/favicon.png'>"
            % self.version
        )
        page += self.navbar_item("/", "Home")
        page += self.navbar_item("/policy", "Policy")
        page += self.navbar_item("#", "Schedule")
        page += self.navbar_item("/settings", "Settings")
        page += self.navbar_item("/debug", "Debug")
        page += self.navbar_item("https://github.com/ngardiner/TWCManager", "GitHub")
        page += "<span class='navbar-text'>%s</span></nav>" % self.version
        return page

    def navbar_item(self, url, name):
        active = ""
        urlp = urllib.parse.urlparse(self.path)
        if urlp.path == url:
            active = "active"
        page = "<ul class='navbar-nav mr-auto'>"
        page += "<li class='nav-item %s'>" % active
        page += "<a class='nav-link' href='%s'>%s</a>" % (url, name)
        page += "</li></ul>"
        return page

    def do_API_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/getConfig":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(self.server.master.config)
            # Scrub output of passwords and API keys
            json_datas = re.sub(r'"password": ".*?",', "", json_data)
            json_data = re.sub(r'"apiKey": ".*?",', "", json_datas)
            self.wfile.write(json_data.encode("utf-8"))

        elif url.path == "/api/getPolicy":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(
                self.server.master.getModuleByName("Policy").charge_policy
            )
            self.wfile.write(json_data.encode("utf-8"))

        elif url.path == "/api/getSlaveTWCs":
            data = {}
            totals = {
                "lastAmpsOffered": 0,
                "lifetimekWh": 0,
                "maxAmps": 0,
                "reportedAmpsActual": 0,
            }
            for slaveTWC in self.server.master.getSlaveTWCs():
                TWCID = "%02X%02X" % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
                data[TWCID] = {
                    "currentVIN": slaveTWC.currentVIN,
                    "lastAmpsOffered": "%.2f" % float(slaveTWC.lastAmpsOffered),
                    "lastHeartbeat": "%.2f" % float(time.time() - slaveTWC.timeLastRx),
                    "lastVIN": slaveTWC.lastVIN,
                    "lifetimekWh": str(slaveTWC.lifetimekWh),
                    "maxAmps": float(slaveTWC.maxAmps),
                    "reportedAmpsActual": "%.2f" % float(slaveTWC.reportedAmpsActual),
                    "state": str(slaveTWC.reportedState),
                    "version": str(slaveTWC.protocolVersion),
                    "voltsPhaseA": str(slaveTWC.voltsPhaseA),
                    "voltsPhaseB": str(slaveTWC.voltsPhaseB),
                    "voltsPhaseC": str(slaveTWC.voltsPhaseC),
                    "TWCID": "%s" % TWCID,
                }
                totals["lastAmpsOffered"] += slaveTWC.lastAmpsOffered
                totals["lifetimekWh"] += slaveTWC.lifetimekWh
                totals["maxAmps"] += slaveTWC.maxAmps
                totals["reportedAmpsActual"] += slaveTWC.reportedAmpsActual

            data["total"] = {
                "lastAmpsOffered": "%.2f" % float(totals["lastAmpsOffered"]),
                "lifetimekWh": totals["lifetimekWh"],
                "maxAmps": totals["maxAmps"],
                "reportedAmpsActual": "%.2f" % float(totals["reportedAmpsActual"]),
                "TWCID": "total",
            }

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(data)
            self.wfile.write(json_data.encode("utf-8"))

        elif url.path == "/api/getStatus":
            data = {
                "carsCharging": self.server.master.num_cars_charging_now(),
                "chargerLoadWatts": "%.2f" % float(self.server.master.getChargerLoad()),
                "currentPolicy": str(
                    self.server.master.getModuleByName("Policy").active_policy
                ),
                "maxAmpsToDivideAmongSlaves": "%.2f"
                % float(self.server.master.getMaxAmpsToDivideAmongSlaves()),
            }
            consumption = float(self.server.master.getConsumption())
            if consumption:
                data["consumptionAmps"] = (
                    "%.2f" % self.server.master.convertWattsToAmps(consumption),
                )
                data["consumptionWatts"] = "%.2f" % consumption
            else:
                data["consumptionAmps"] = "%.2f" % 0
                data["consumptionWatts"] = "%.2f" % 0
            generation = float(self.server.master.getGeneration())
            if generation:
                data["generationAmps"] = (
                    "%.2f" % self.server.master.convertWattsToAmps(generation),
                )
                data["generationWatts"] = "%.2f" % generation
            else:
                data["generationAmps"] = "%.2f" % 0
                data["generationWatts"] = "%.2f" % 0
            if self.server.master.getModuleByName("Policy").policyIsGreen():
                data["isGreenPolicy"] = "Yes"
            else:
                data["isGreenPolicy"] = "No"

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(data)
            self.wfile.write(json_data.encode("utf-8"))

        elif url.path == "/api/getHistory":
            output = []
            now = datetime.now().replace(second=0, microsecond=0).astimezone()
            startTime = now - timedelta(days=2) + timedelta(minutes=5)
            endTime = now.replace(minute=math.floor(now.minute / 5) * 5)
            startTime = startTime.replace(minute=math.floor(startTime.minute / 5) * 5)

            source = (
                self.server.master.settings["history"]
                if "history" in self.server.master.settings
                else []
            )
            data = {k: v for k, v in source if datetime.fromisoformat(k) >= startTime}

            avgCurrent = 0
            for slave in self.server.master.getSlaveTWCs():
                avgCurrent += slave.historyAvgAmps
            data[
                endTime.isoformat(timespec="seconds")
            ] = self.server.master.convertAmpsToWatts(avgCurrent)

            output = [
                {
                    "timestamp": timestamp,
                    "charger_power": data[timestamp] if timestamp in data else 0,
                }
                for timestamp in [
                    (startTime + timedelta(minutes=5 * i)).isoformat(timespec="seconds")
                    for i in range(48 * 12)
                ]
            ]

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            json_data = json.dumps(output)
            self.wfile.write(json_data.encode("utf-8"))

        else:
            # All other routes missed, return 404
            self.send_response(404)
            self.end_headers()
            self.wfile.write("".encode("utf-8"))

    def do_API_POST(self):

        if self.url.path == "/api/chargeNow":
            data = json.loads(self.post_data.decode("UTF-8"))
            rate = int(data.get("chargeNowRate", 0))
            durn = int(data.get("chargeNowDuration", 0))

            if rate == 0 or durn == 0:
                self.send_response(400)
                self.end_headers()
                return

            self.server.master.setChargeNowAmps(rate)
            self.server.master.setChargeNowTimeEnd(durn)
            self.server.master.saveSettings()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return

        if self.url.path == "/api/cancelChargeNow":
            self.server.master.resetChargeNowAmps()
            self.server.master.saveSettings()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return

        if self.url.path == "/api/sendStartCommand":
            self.server.master.sendStartCommand()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return

        if self.url.path == "/api/sendStopCommand":
            self.server.master.sendStopCommand()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            return

        # All other routes missed, return 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write("".encode("utf-8"))
        return

    def do_get_debug(self):
        page = "<html><head>"
        page += "<title>TWCManager</title>"
        page += self.do_bootstrap()
        page += self.do_css()
        page += self.do_jsrefresh()
        page += "</head>"
        page += "<body>"
        page += self.do_navbar()
        page += """
          Debug Interface - Coming soon
        </body>
        </html>
        """
        return page

    def do_get_policy(self):
        page = "<html><head>"
        page += "<title>TWCManager</title>"
        page += self.do_bootstrap()
        page += self.do_css()
        page += self.do_jsrefresh()
        page += "</head>"
        page += "<body>"
        page += self.do_navbar()
        page += """
      <table>
        """
        j = 0
        for policy in self.server.master.getModuleByName("Policy").charge_policy:
            if j == 0:
                page += "<tr><th>Policy Override Point</th></tr>"
                page += "<tr><td>Emergency</td></tr>"
            if j == 1:
                page += "<tr><th>Policy Override Point</th></tr>"
                page += "<tr><td>Before</td></tr>"
            if j == 3:
                page += "<tr><th>Policy Override Point</th></tr>"
                page += "<tr><td>After</td></tr>"
            j += 1
            page += "<tr><td>&nbsp;</td><td>" + policy["name"] + "</td></tr>"
            page += "<tr><th>&nbsp;</th><th>&nbsp;</th><th>Match Criteria</th><th>Condition</th><th>Value</th></tr>"
            for i in range(0, len(policy["match"])):
                page += "<tr><td>&nbsp;</td><td>&nbsp;</td>"
                page += "<td>" + policy["match"][i] + "</td>"
                page += "<td>" + policy["condition"][i] + "</td>"
                page += "<td>" + str(policy["value"][i]) + "</td></tr>"

        page += """
      </table>
    </body>
        """
        return page

    def do_get_settings(self):
        page = "<html><head>"
        page += "<title>TWCManager</title>"
        page += self.do_bootstrap()
        page += self.do_css()
        page += self.do_jsrefresh()
        page += "</head>"
        page += "<body>"
        page += self.do_navbar()
        page += """
    <html>
    <head><title>Settings</title></head>
    <body>
    <form method=POST action='/settings/save'>
      <table>
        <tr>
          <th>Stop Charging Method</th>
          <td>
        """
        page += self.optionList(
            [
                [1, "Tesla API"],
                [2, "Stop Responding to Slaves"],
                [3, "Send Stop Command"],
            ],
            {
                "name": "chargeStopMode",
                "value": self.server.master.settings.get("chargeStopMode", "1"),
            },
        )
        page += """
          </td>
        </tr>
        <tr>
          <th>Non-scheduled power charge rate:</th>
          <td>
        """
        page += self.optionList(
            [[6, "6A"], [8, "8A"], [10, "10A"], [12, "12A"], [24, "24A"], [32, "32A"]],
            {
                "name": "nonScheduledPower",
                "value": self.server.master.settings.get("nonScheduledPower", "6"),
            },
        )
        page += """
          </td>
        </tr>
        <tr>
          <td>&nbsp;</td>
          <td><input class='btn btn-outline-success' type=submit value='Save Settings' /></td>
        </tr>
      </table>
    </form>
        """
        page += (
            "<p>Click <a href='https://github.com/ngardiner/TWCManager/tree/%s/docs/Settings.md' target='_new'>here</a> for detailed information on settings on this page</p>"
            % self.version
        )
        page += "</body></html>"
        return page

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        if url.path.startswith("/api/"):
            self.do_API_GET()
            return

        if (
            url.path == "/"
            or url.path == "/apiacct/True"
            or url.path == "/apiacct/False"
        ):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Send the html message
            page = "<html><head>"
            page += "<title>TWCManager</title>"
            page += self.do_bootstrap()
            page += self.do_css()
            page += self.do_jsrefresh()
            page += "</head>"
            page += "<body>"
            page += self.do_navbar()
            page += "<table border='0' padding='0' margin='0' width='100%'>"
            page += "<tr width='100%'><td valign='top' width='70%'>"

            if url.path == "/apiacct/False":
                page += "<font color='red'><b>Failed to log in to Tesla Account. Please check username and password and try again.</b></font>"

            if (
                not self.server.master.teslaLoginAskLater
                and url.path != "/apiacct/True"
            ):
                # Check if we have already stored the Tesla credentials
                # If we can access the Tesla API okay, don't prompt
                if not self.server.master.getModuleByName(
                    "TeslaAPI"
                ).car_api_available():
                    page += self.request_teslalogin()

            if url.path == "/apiacct/True":
                page += "<b>Thank you, successfully fetched Tesla API token."

            page += self.show_status()
            page += "</td><td valign=top width='30%'>"
            page += self.do_chargeSchedule()
            page += "</td></tr>"
            page += "</table>"
            page += "</body>"
            page += "</table>"
            page += "</html>"

            self.wfile.write(page.encode("utf-8"))
            return

        if url.path == "/debug":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            page = self.do_get_debug()
            self.wfile.write(page.encode("utf-8"))
            return

        if url.path == "/policy":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            page = self.do_get_policy()
            self.wfile.write(page.encode("utf-8"))
            return

        if url.path == "/settings":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            page = self.do_get_settings()
            self.wfile.write(page.encode("utf-8"))
            return

        if url.path == "/tesla-login":
            # For security, these details should be submitted via a POST request
            # Send a 405 Method Not Allowed in response.
            self.send_response(405)
            page = "This function may only be requested via the POST HTTP method."
            self.wfile.write(page.encode("utf-8"))
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

        if self.url.path == "/settings/save":
            # User has submitted settings.
            # Call dedicated function
            self.process_settings()
            return

        if self.url.path == "/tesla-login":
            # User has submitted Tesla login.
            # Pass it to the dedicated process_teslalogin function
            self.process_teslalogin()
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
        page = "<input type='Submit' %s id='%s' value='%s'>" % (
            extrargs,
            button_def[0],
            button_def[1],
        )
        return page

    def log_message(self, format, *args):
        pass

    def optionList(self, list, opts={}):
        page = "<div class='form-group'>"
        page += "<select class='form-control' id='%s'>" % opts.get("name", "")
        for option in list:
            sel = ""
            if str(opts.get("value", "-1")) == str(option[0]):
                sel = "selected"
            page += "<option value='%s' %s>%s</option>" % (option[0], sel, option[1])
        page += "</div>"
        page += "</select>"
        return page

    def process_settings(self):

        # Write settings
        for key in self.fields:
            keya = str(key)
            vala = self.fields[key][0].replace("'", "")
            self.server.master.settings[keya] = vala
        self.server.master.saveSettings()

        # Redirect to the index page
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()
        self.wfile.write("".encode("utf-8"))
        return

    def process_teslalogin(self):
        # Check if we are skipping Tesla Login submission

        if not self.server.master.teslaLoginAskLater:
            later = False
            try:
                later = len(self.fields["later"])
            except KeyError as e:
                later = False

            if later:
                self.server.master.teslaLoginAskLater = True

        if not self.server.master.teslaLoginAskLater:
            # Connect to Tesla API

            carapi = self.server.master.getModuleByName("TeslaAPI")
            carapi.setCarApiLastErrorTime(0)
            ret = carapi.car_api_available(
                self.fields["email"][0], self.fields["password"][0]
            )

            # Redirect to an index page with output based on the return state of
            # the function
            self.send_response(302)
            self.send_header("Location", "/apiacct/" + str(ret))
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return
        else:
            # User has asked to skip Tesla Account submission for this session
            # Redirect back to /
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            self.wfile.write("".encode("utf-8"))
            return

    def request_teslalogin(self):
        page = "<form action='/tesla-login' method='POST'>"
        page += "<p>Enter your email and password to allow TWCManager to start and "
        page += "stop Tesla vehicles you own from charging. These credentials are "
        page += "sent once to Tesla and are not stored. Credentials must be entered "
        page += "again if no cars are connected to this charger for over 45 days."
        page += "</p>"
        page += "<input type=hidden name='page' value='tesla-login' />"
        page += "<p>"
        page += "<table>"
        page += "<tr><td>Tesla Account E-Mail:</td>"
        page += "<td><input type='text' name='email' value=''></td></tr>"
        page += "<tr><td>Password:</td>"
        page += "<td><input type='password' name='password'></td></tr>"
        page += "<tr><td><input type='submit' name='submit' value='Log In'></td>"
        page += "<td><input type='submit' name='later' value='Ask Me Later'></td>"
        page += "</tr>"
        page += "</table>"
        page += "</p>"
        page += "</form>"
        return page

    def show_commands(self):

        page = """
          <table class='table table-dark'>
          <tr><th colspan=4 width = '30%'>Charge Now</th>
          <th colspan=1 width = '30%'>Commands</th></tr>
          <tr><td width = '8%'>Charge for:</td>
          <td width = '7%'>
        """
        hours = []
        for hour in range(1, 25):
            hours.append([(hour * 3600), str(hour) + "h"])
        page += self.optionList(hours, {"name": "chargeNowDuration"})
        page += """
          </td>
          <td width = '8%'>Charge Rate:</td>
          <td width = '7%'>
        """
        amps = []
        maxamps = self.server.master.config["config"].get("wiringMaxAmpsPerTWC", 5)
        for amp in range(5, (maxamps + 1)):
            amps.append([amp, str(amp) + "A"])
        page += self.optionList(amps, {"name": "chargeNowRate"})
        page += """
          </td>
          <td>
        """
        page += self.addButton(
            ["send_stop_command", "Stop All Charging"],
            "class='btn btn-outline-danger' data-toggle='tooltip' data-placement='top' title='WARNING: This function causes Tesla Vehicles to Stop Charging until they are physically re-connected to the TWC.'",
        )
        page += """
          </td></tr>
          <tr><td colspan = '2'>
        """
        page += self.addButton(
            ["start_chargenow", "Start Charge Now"],
            "class='btn btn-outline-success' data-toggle='tooltip' data-placement='top' title='Note: Charge Now command takes approximately 2 minutes to activate.'",
        )
        page += "</td><td colspan = '2'>"
        page += self.addButton(
            ["cancel_chargenow", "Cancel Charge Now"], "class='btn btn-outline-danger'"
        )
        page += """
          </td>
          <td>
        """
        page += self.addButton(
            ["send_start_command", "Start All Charging"],
            "class='btn btn-outline-success'",
        )
        page += """
          </td></tr>
          </table>
        """
        return page

    def show_status(self):

        page = """
        <table width='100%'><tr><td width='60%'>
        <table class='table table-dark'>
        <tr>
          <th>Amps to share across all TWCs:</th>
          <td><div id='maxAmpsToDivideAmongSlaves'></div></td><td>amps</td>
        </tr>
        <tr>
          <th>Current Generation</th>
          <td><div id='generationWatts'></div></td><td>watts</td>
          <td><div id="generationAmps"></div></td><td>amps</td>
        </tr>
        <tr>
          <th>Current Consumption</th>
          <td><div id='consumptionWatts'></div></td><td>watts</td>
          <td><div id='consumptionAmps'></div></td><td>amps</td>
        </tr>
        <tr>
          <th>Current Charger Load</th>
          <td><div id="chargerLoadWatts"></div></td><td>watts</td>
        </tr>
        <tr>
          <th>Number of Cars Charging</th>
          <td><div id="carsCharging"></div></td>
          <td>cars</td>
        </tr>
        </table></td>
        """

        page += "<td width='40%'>"
        page += "<table class='table table-dark'>"
        page += "<tr><th>Current Policy</th>"
        page += "<td><div id='currentPolicy'></div></td></tr>"
        page += "<tr><th>Scheduled Charging Amps</th>"
        page += "<td>" + str(self.server.master.getScheduledAmpsMax()) + "</td></tr>"

        page += "<tr><th>Scheduled Charging Start Hour</th>"
        page += (
            "<td>" + str(self.server.master.getScheduledAmpsStartHour()) + "</td></tr>"
        )

        page += "<tr><th>Scheduled Charging End Hour</th>"
        page += "<td>" + str(self.server.master.getScheduledAmpsEndHour()) + "</td>"
        page += """
        </tr>
        <tr>
          <th>Is a Green Policy?</th>
          <td><div id='isGreenPolicy'></div></td>
        </tr>
        </table></td>
        """

        page += "<tr><td width = '100%' colspan = '2'>"
        page += self.show_twcs()
        page += "</td></tr>"

        page += "<tr><td width = '100%' colspan = '2'>"
        page += self.show_commands()
        page += "</td></tr></table>"
        return page

    def show_twcs(self):

        page = """
        <table><tr width = '100%'><td width='65%'>
          <table class='table table-dark table-condensed table-striped'>
          <thead class='thead-dark'><tr>
            <th width='2%'>TWC ID</th>
            <th width='1%'>State</th>
            <th width='1%'>Version</th>
            <th width='2%'>Max Amps</th>
            <th width='2%'>Amps<br />Offered</th>
            <th width='2%'>Amps<br />In Use</th>
            <th width='2%'>Lifetime<br />kWh</th>
            <th width='4%'>Voltage<br />per Phase<br />1 / 2 / 3</th>
            <th width='2%'>Last Heartbeat</th>
            <th width='6%'>Vehicle Connected<br />Current / Last</th>
            <th width='2%'>Commands</th>
          </tr></thead>
        """
        for slaveTWC in self.server.master.getSlaveTWCs():
            twcid = "%02X%02X" % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
            page += "<tr>"
            page += "<td>%s</td>" % twcid
            page += "<td><div id='%s_state'></div></td>" % twcid
            page += "<td><div id='%s_version'></div></td>" % twcid
            page += "<td><div id='%s_maxAmps'></div></td>" % twcid
            page += "<td><div id='%s_lastAmpsOffered'></div></td>" % twcid
            page += "<td><div id='%s_reportedAmpsActual'></div></td>" % twcid
            page += "<td><div id='%s_lifetimekWh'></div></td>" % twcid
            page += (
                "<td><span id='%s_voltsPhaseA'></span> / <span id='%s_voltsPhaseB'></span> / <span id='%s_voltsPhaseC'></span></td>"
                % (twcid, twcid, twcid)
            )
            page += "<td><span id='%s_lastHeartbeat'></span> sec</td>" % twcid
            page += (
                "<td>C: <span id='%s_currentVIN'></span><br />L: <span id='%s_lastVIN'></span></td>"
                % (twcid, twcid)
            )
            page += """
            <td>
              <div class="dropdown">
                <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Select</button>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                  <a class="dropdown-item" href="#">Coming Soon</a>
                </div>
              </div>
            </td>
            """
            page += "</tr>\n"
        page += "<tr><td><b>Total</b><td>&nbsp;</td><td>&nbsp;</td>"
        page += "<td><div id='total_maxAmps'></div></td>"
        page += "<td><div id='total_lastAmpsOffered'></div></td>"
        page += "<td><div id='total_reportedAmpsActual'></div></td>"
        page += "<td><div id='total_lifetimekWh'></div></td>"
        page += "</tr></table></td></tr></table>"
        return page
