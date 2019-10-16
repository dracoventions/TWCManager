from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import urllib.parse

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
  pass

class HTTPControl:

  PORT = 8080

  def __init__(self):

    httpd = ThreadingSimpleServer(("", self.PORT), HTTPControlHandler)
    print("serving at port", self.PORT)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

class HTTPControlHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    url = urllib.parse.urlparse(self.path)
    #ParseResult(scheme='', netloc='', path='/', params='', query='', fragment='')
    print(url.path)

    if (url.path == '/'):
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      # Send the html message
      page = "<html><head>"
      page += "<title>TWCManager</title>"
      page += "<link rel='icon' type='image/png' href='favicon.png'>"
      page += "<meta name='viewport' content='width=device-width, initial-scale=1'>"
      page += "</head>"
      page += "<form action='/' name='refresh' method='get'>"
      page += "<table border='0' padding='0' margin='0'><tr>"
      page += "<td valign='top'>"

      self.wfile.write(page.encode("utf-8"))
      return

