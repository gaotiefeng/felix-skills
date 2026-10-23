"""Local synthetic API fixture used by smoke.py; never contacts external services."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time

SECRET_MARKER = 'MOCK_UPSTREAM_SECRET_DO_NOT_RETURN'
MOCK_TOKEN = 'mock-only-not-a-real-token'


def create_mock():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            requests.append(self.path)
            order_id = self.path.rsplit('/', 1)[-1]
            code, content_type = 200, 'application/json'
            body = json.dumps({'order_id': order_id, 'status': 'in_transit'}).encode()
            if self.headers.get('Authorization') != f'Bearer {MOCK_TOKEN}':
                code, body = 401, SECRET_MARKER.encode()
            elif order_id in ('AUTH', 'FORBIDDEN', 'MISSING', 'LIMITED', 'BROKEN'):
                code = {'AUTH': 401, 'FORBIDDEN': 403, 'MISSING': 404, 'LIMITED': 429, 'BROKEN': 500}[order_id]
                body = SECRET_MARKER.encode()
            elif order_id == 'BADJSON':
                body = b'{not JSON'
            elif order_id == 'BADSHAPE':
                body = json.dumps({'unexpected': SECRET_MARKER}).encode()
            elif order_id == 'WRONGID':
                body = json.dumps({'order_id': 'OTHER', 'status': 'in_transit'}).encode()
            elif order_id == 'TOOBIG':
                body = json.dumps({'value': 'x' * 70000}).encode()
            elif order_id == 'WRONGTYPE':
                content_type = 'text/html'
                body = b'<html>not an API response</html>'
            elif order_id == 'REDIRECT':
                code, body = 302, b''
            elif order_id == 'SLOW':
                time.sleep(1)
            elif order_id == 'EXTRA':
                body = json.dumps({'order_id': order_id, 'status': 'in_transit', 'token': SECRET_MARKER}).encode()
            try:
                self.send_response(code)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                if code == 302:
                    self.send_header('Location', '/should-not-follow')
                if code == 429:
                    self.send_header('Retry-After', '1')
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Expected when a test intentionally aborts a slow/large response.

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    return server, requests
