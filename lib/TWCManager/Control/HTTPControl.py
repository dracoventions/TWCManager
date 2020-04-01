from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from termcolor import colored
import threading
import time
import urllib.parse
from ww import f

# Global reference to master
master = None


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

        if self.status:
            httpd = ThreadingSimpleServer(("", self.httpPort), HTTPControlHandler)
            self.master.debugLog(
                1, "HTTPCtrl  ", "Serving at port: " + str(self.httpPort)
            )
            threading.Thread(target=httpd.serve_forever, daemon=True).start()


class HTTPControlHandler(BaseHTTPRequestHandler):

    fields = {}

    def do_css(self):

        page = "<style>"
        page += """
      table.darkTable {
        font-family: 'Arial Black', Gadget, sans-serif;
        border: 2px solid #000000;
        background-color: #717171;
        width: 40%;
        height: 200px;
        text-align: center;
        border-collapse: collapse;
      }
      table.darkTable td, table.darkTable th {
        border: 1px solid #4A4A4A;
        padding: 3px 2px;
      }
      table.darkTable tbody td {
        font-size: 13px;
        color: #E6E6E6;
      }
      table.darkTable tr:nth-child(even) {
        background: #888888;
      }
      table.darkTable thead {
        background: #000000;
        border-bottom: 3px solid #000000;
      }
      table.darkTable thead th {
        font-size: 15px;
        font-weight: bold;
        color: #E6E6E6;
        text-align: center;
        border-left: 2px solid #4A4A4A;
      }
      table.darkTable thead th:first-child {
        border-left: none;
      }
      table.darkTable tfoot td {
        font-size: 12px;
      }
      #vertical thead,#vertical tbody{
        display:inline-block;
      }
      
      """
        page += "</style>"
        return page

    def do_chargeSchedule(self):
        page = """
    <table class='table table-borderless'>
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
        for i in (x for y in (range(6, 24), range(0, 5)) for x in y):
            page += "<tr><th scope='row'>%02d</th><td>&nbsp;</td></tr>" % (i)
        page += "</tbody>"
        page += "</table>"

        return page

    def do_jsrefresh(self):
        page = """
      // Only refresh the main page if the browser window has focus, and if
      // the input form does not have focus
      <script language = 'JavaScript'>
      var formFocus = false;
      var hasFocus= true;

      function formNoFocus() {
        formFocus = false;
      }

      function formHasFocus() {
        formFocus = true;
      }

      window.onblur = function() {
        hasFocus = false;
      }
      window.onfocus = function(){
        hasFocus = true;
      }
      setInterval(reload, 5*1000);
      function reload(){
          if(hasFocus && !formFocus){
              location.reload(true);
          }
      }
      </script> """
        return page

    def do_navbar(self):
        page = """
    <p>&nbsp;</p>
    <p>&nbsp;</p>
    <nav class='navbar fixed-top navbar-dark bg-dark' role='navigation'>
      <a class='navbar-brand' href='/'>TWCManager</a>
      <link rel='icon' type='image/png' href='https://raw.githubusercontent.com/ngardiner/TWCManager/master/tree/v1.1.8/html/favicon.png'>
      <ul class="navbar-nav mr-auto">
        <li class="nav-item active">
          <a class="nav-link" href="#">Home</a>
        </li>
      </ul>
      <ul class="navbar-nav mr-auto">
        <li class="nav-item">
          <a class="nav-link" href="#">Schedule</a>
        </li>
      </ul>
      <ul class="navbar-nav mr-auto">
        <li class="nav-item">
          <a class="nav-link" href="/settings">Settings</a>
        </li>
      </ul>
      <ul class='navbar-nav mr-auto'>
        <li class='nav-item'>
          <a class='nav-link' href='https://github.com/ngardiner/TWCManager'>GitHub</a>
        </li>
      </ul>
      <span class="navbar-text">v1.1.8</span>
    </nav>"""
        return page

    def do_get_settings(self):
        page = """
    <html>
    <head><title>Settings</title></head>
    <body>
    <form method=POST action='/settings/save'>
      <table>
        <tr>
          <th>Stop Charging Method</th>
          <td>
  <select name='chargeStopMode'>"""
        page += '<option value="1" '
        if master.settings.get("chargeStopMode", "1") == "1":
            page += "selected"
        page += ">Tesla API</option>"
        page += '<option value="2" '
        if master.settings.get("chargeStopMode", "1") == "2":
            page += "selected"
        page += ">Stop Responding to Slaves</option>"
        page += """
  </select>
          </td>
        </tr>
        <tr>
          <td>&nbsp;</td>
          <td><input type=submit /></td>
        </tr>
      </table>
    </form>
    </body>
    </html>
    """
        return page

    def do_GET(self):
        global master
        url = urllib.parse.urlparse(self.path)

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
            page += (
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            )
            page += "<link rel='stylesheet' href='https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css' integrity='sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T' crossorigin='anonymous'>"
            page += self.do_css()
            page += self.do_jsrefresh()
            page += "</head>"
            page += "<body>"
            page += self.do_navbar()
            page += "<table border='0' padding='0' margin='0'><tr>"
            page += "<td valign='top'>"

            if url.path == "/apiacct/False":
                page += "<font color='red'><b>Failed to log in to Tesla Account. Please check username and password and try again.</b></font>"

            if not master.teslaLoginAskLater and url.path != "/apiacct/True":
                page += self.request_teslalogin()

            if url.path == "/apiacct/True":
                page += "<b>Thank you, successfully fetched Tesla API token."

            page += self.show_status()

            page += "</table>"
            page += "</body>"
            page += "</table>"
            page += "</html>"

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
        global master

        # Parse URL
        url = urllib.parse.urlparse(self.path)

        # Parse POST parameters
        self.fields.clear()
        length = int(self.headers.get("content-length"))
        field_data = self.rfile.read(length)
        self.fields = urllib.parse.parse_qs(str(field_data))

        if url.path == "/settings/save":
            # User has submitted settings.
            # Call dedicated function
            self.process_settings()
            return

        if url.path == "/tesla-login":
            # User has submitted Tesla login.
            # Pass it to the dedicated process_teslalogin function
            self.process_teslalogin()
            return

        # All other routes missed, return 404
        self.send_response(404)
        self.end_headers()
        self.wfile.write("".encode("utf-8"))
        return

    def process_settings(self):

        # Write settings
        for key in self.fields:
            keya = str(key).replace("b'", "")
            vala = self.fields[key][0].replace("'", "")
            master.settings[keya] = vala
        master.saveSettings()

        # Redirect to the index page
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()
        self.wfile.write("".encode("utf-8"))
        return

    def process_teslalogin(self):
        # Check if we are skipping Tesla Login submission

        if not master.teslaLoginAskLater:
            later = False
            try:
                later = len(self.fields["later"])
            except KeyError as e:
                later = False

            if later:
                master.teslaLoginAskLater = True

        if not master.teslaLoginAskLater:
            # Connect to Tesla API

            carapi = self.master.getModuleByName("TeslaAPI")
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
        page += "<td><input type='text' name='email' value='' onFocus='formHasFocus()' onBlur='formNoFocus()'></td></tr>"
        page += "<tr><td>Password:</td>"
        page += "<td><input type='password' name='password' onFocus='formHasFocus()' onBlur='formNoFocus()'></td></tr>"
        page += "<tr><td><input type='submit' name='submit' value='Log In'></td>"
        page += "<td><input type='submit' name='later' value='Ask Me Later'></td>"
        page += "</tr>"
        page += "</table>"
        page += "</p>"
        page += "</form>"
        return page

    def show_status(self):
        global master

        page = "<table width = '100%'><tr width = '100%'><td width='30%'>"
        page += "<table class='table table-dark' width='100%'>"
        page += "<tr><th>Amps to share across all TWCs:</th>"
        page += "<td>" + str(master.getMaxAmpsToDivideAmongSlaves()) + "</td>"
        page += "<td>amps</td></tr>"

        page += "<tr><th>Current Generation</th>"
        page += "<td>" + str(master.getGeneration()) + "</td>"
        page += "<td>watts</td>"
        genamps = 0
        if master.getGeneration():
            genamps = master.getGeneration() / 240
        page += "<td>" + str(genamps) + "</td><td>amps</td></tr>"

        page += "<tr><th>Current Consumption</th>"
        page += "<td>" + str(master.getConsumption()) + "</td>"
        page += "<td>watts</td>"
        conamps = 0
        if master.getConsumption():
            conamps = master.getConsumption() / 240
        page += "<td>" + str(conamps) + "</td><td>amps</td></tr>"

        page += "<tr><th>Current Charger Load</th>"
        page += "<td>" + str(master.getChargerLoad()) + "</td>"
        page += "<td>watts</td>"
        page += "</tr>"

        page += "<tr><th>Number of Cars Charging</th>"
        page += "<td>" + str(master.num_cars_charging_now()) + "</td>"
        page += "<td>cars</td></tr></table></td>"

        page += "<td width='30%'>"
        page += "<table class='table table-dark' width='100%'>"
        page += "<tr><th>Scheduled Charging Amps</th>"
        page += "<td>" + str(master.getScheduledAmpsMax()) + "</td></tr>"

        page += "<tr><th>Scheduled Charging Start Hour</th>"
        page += "<td>" + str(master.getScheduledAmpsStartHour()) + "</td></tr>"

        page += "<tr><th>Scheduled Charging End Hour</th>"
        page += "<td>" + str(master.getScheduledAmpsEndHour()) + "</td>"
        page += "</tr>"

        page += "<tr><th>Resume Tracking Green Energy at</th>"
        page += "<td>" + str(master.getHourResumeTrackGreenEnergy()) + "</td>"
        page += "</tr>"
        page += "</table></td>"

        page += "<td width = '40%' rowspan = '3'>"
        page += self.do_chargeSchedule()
        page += "</td></tr>"
        page += "<tr><td>"
        page += self.show_twcs()
        page += "</td></tr>"

        # Handle overflow from calendar
        page += "<tr><td>&nbsp;</td></tr></table>"
        return page

    def show_twcs(self):
        global master

        page = "<table class='darkTable'>\n"
        page += "<thead><tr>"
        page += "<th>TWC ID</th>"
        page += "<th>State</th>"
        page += "<th>Version</th>"
        page += "<th>Max Amps</th>"
        page += "<th>Amps Offered</th>"
        page += "<th>Amps In Use</th>"
        page += "<th>Last Heartbeat</th>"
        page += "</tr></thead>\n"
        lastAmpsTotal = 0
        maxAmpsTotal = 0
        totalAmps = 0
        for slaveTWC in master.getSlaveTWCs():
            page += "<tr>"
            page += "<td>%02X%02X</td>" % (slaveTWC.TWCID[0], slaveTWC.TWCID[1])
            page += "<td>" + str(slaveTWC.reportedState) + "</td>"
            page += "<td>" + str(slaveTWC.protocolVersion) + "</td>"
            page += "<td>%.2f</td>" % float(slaveTWC.maxAmps)
            maxAmpsTotal += float(slaveTWC.maxAmps)
            page += "<td>%.2f</td>" % float(slaveTWC.lastAmpsOffered)
            lastAmpsTotal += float(slaveTWC.lastAmpsOffered)
            page += "<td>%.2f</td>" % float(slaveTWC.reportedAmpsActual)
            totalAmps += float(slaveTWC.reportedAmpsActual)
            page += "<td>%.2f sec</td>" % float(time.time() - slaveTWC.timeLastRx)
            page += "</tr>\n"
        page += "<tr><td><b>Total</b><td>&nbsp;</td><td>&nbsp;</td>"
        page += "<td>%.2f</td>" % float(maxAmpsTotal)
        page += "<td>%.2f</td>" % float(lastAmpsTotal)
        page += "<td>%.2f</td>" % float(totalAmps)
        page += "</tr></table>\n"
        return page
