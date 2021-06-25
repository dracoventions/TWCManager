#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler

class MyRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        # Extract values from the query string
        path, _, query_string = self.path.partition('?')
        query = parse_qs(query_string)

        self.send_response(200)
        self.end_headers()

        if path == "/api/all/power/now":
            self.wfile.write(emulate_SmartPi())

    def emulate_SmartPi():
        return('{"serial":"smartpi123412345","name":"House","lat":111.1111,"lng":2.2222,"time":"2021-03-22 19:36:38","softwareversion":"","ipaddress":"192.168.1.3","datasets":[{"time":"2021-03-22 19:36:38","phases":[{"phase":1,"name":"phase 1","values":[{"type":"power","unity":"W","info":"","data":168.92613}]},{"phase":2,"name":"phase 2","values":[{"type":"power","unity":"W","info":"","data":212.23642}]},{"phase":3,"name":"phase 3","values":[{"type":"power","unity":"W","info":"","data":91.89515}]},{"phase":4,"name":"phase 4","values":[{"type":"power","unity":"W","info":"","data":0}]}]}]}');

httpd = HTTPServer(('localhost', 1080), MyRequestHandler)
httpd.serve_forever()
