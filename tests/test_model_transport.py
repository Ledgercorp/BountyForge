"""Real loopback HTTP denial tests, without inference or external requests."""
import http.server
import threading
import time
import socket
import unittest
from bountyforge.model import LocalModel

class ModelTransportTests(unittest.TestCase):
    def serve(self, mode):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                if mode=='timeout':
                    time.sleep(0.08)
                    return
                self.send_response(302)
                self.send_header('Location','https://example.invalid/should-never-be-requested')
                self.end_headers()
        server=http.server.HTTPServer(('127.0.0.1',18080),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return LocalModel('http://127.0.0.1:18080/v1/chat/completions',timeout_seconds=0.02)
    def test_real_model_transport_timeout_fails_closed(self):
        model=self.serve('timeout')
        with self.assertRaises(RuntimeError):model.complete_line('system','{}')
        self.assertIsNone(model.last_call)
    def test_actual_http_redirect_cannot_escape_loopback(self):
        model=self.serve('redirect')
        with self.assertRaises(RuntimeError):model.complete_line('system','{}')
        self.assertIsNone(model.last_call)
    def test_real_unavailable_endpoint_fails_closed(self):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            sock.bind(('127.0.0.1',18080))
        model=LocalModel('http://127.0.0.1:18080/v1/chat/completions',timeout_seconds=0.02)
        with self.assertRaises(RuntimeError):model.complete_line('system','{}')
    def test_timeout_budget_cannot_be_disabled(self):
        for value in (0,46,True,float('inf')):
            with self.assertRaises(ValueError):LocalModel(timeout_seconds=value)
