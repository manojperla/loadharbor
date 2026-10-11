"""Controlled loopback API for examples, not a production performance benchmark."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

def start_demo():
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def do_GET(self):
            path = urlsplit(self.path).path
            routes = {'/api/products': {'items': [{'id': 1, 'name': 'Engineering book'}]},
                      '/api/products/1': {'id': 1, 'name': 'Engineering book'},
                      '/api/search': {'items': [{'id': 1, 'name': 'Engineering book'}]}}
            status = 200 if path in routes else 404
            body = json.dumps({'ok': status == 200, **routes.get(path, {})}).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
