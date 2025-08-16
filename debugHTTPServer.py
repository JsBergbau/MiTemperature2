#!/usr/bin/env -S python3 -u

from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Path:", self.path)        
        print("Headers:", self.headers)  
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
