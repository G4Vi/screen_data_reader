#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
#import urllib.parse
#from urllib. import parse_qs
#import time
import cgi
import screen_data_reader

hostName = "localhost"
serverPort = 8080

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>Screen Data Dumper</title></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes("<p>Upload video file created by psx_screen_dumper.</p>", "utf-8"))
        self.wfile.write(bytes("<form method=\"post\" action=\"/screen_data_reader.py\" enctype=\"multipart/form-data\">", "utf-8"))
        self.wfile.write(bytes("<input type=\"file\" id=\"myFile\" name=\"file\">", "utf-8"))
        self.wfile.write(bytes("<input type=\"submit\" value=\"Upload\">", "utf-8"))
        self.wfile.write(bytes("</form>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))
    
    def do_POST(self):
        cl = int(self.headers['Content-Length'])
        if cl > 104857600:
            self.send_response(413)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("<h1>Too much data, 100 MiB max</h1>", "utf-8"))
            return
        ctype, pdict = cgi.parse_header(self.headers.get('Content-Type'))
        if ctype == 'multipart/form-data':
            pdict["boundary"] = bytes(pdict["boundary"], "ascii") # embarrassing
            postvars = cgi.parse_multipart(self.rfile, pdict)
        #self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        
        # opencv doesn't allow VideoCapture from buf
        tmpfilename = "uniquefilename.bin"
        f = open(tmpfilename, "wb")
        f.write(postvars["file"][0])
        f.close()

        # try to decode finally
        try:
            filename, thedata = screen_data_reader.fromFile(tmpfilename)
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
            self.end_headers()
            self.wfile.write(bytes(thedata))
            return     
        except:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("<h1>Failed to decode enough frames</h1>", "utf-8"))
            return       

if __name__ == "__main__":        
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")