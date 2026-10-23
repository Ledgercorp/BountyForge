"""Test-owned faulting HTTP process, never imported by application code."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import time

from bountyforge.phase8_synthetic_order import _records


def main():
    scenario = sys.argv[1]
    class Handler(BaseHTTPRequestHandler):
        calls = 0
        def log_message(self, *args):
            pass

        def do_GET(self):
            Handler.calls += 1
            nonce = self.headers.get('X-BountyForge-Simulator-Nonce')
            records = _records('refunded' if scenario == 'refund_on_final' and Handler.calls > 3 else 'paid')
            envelope = {'kind':'phase8_provider_SIMULATOR', 'scenario':'paid',
                        'nonce':nonce, 'record':records[self.path]}
            raw = json.dumps(envelope).encode()
            code = 200
            if scenario == 'malformed': raw = b'{broken'
            elif scenario == 'oversized': raw = b' '*9000
            elif scenario == 'redirect': code = 302
            elif scenario == 'http_error': code = 503
            if scenario == 'expire_on_final' and Handler.calls == 6:
                time.sleep(1.1)
            self.send_response(code)
            if scenario == 'redirect': self.send_header('Location', 'https://api.stripe.com/v1/charges/blocked')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = HTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'provider_simulator':True,'port':server.server_port}), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
