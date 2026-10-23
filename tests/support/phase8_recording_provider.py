"""Independent fixed owned HTTP protocol fixture; imports no application code."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys

SESSION = 'cs_live_BountyForgeSIMULATIONONLY0001'
PAYMENT = 'pi_BountyForgeSIMULATIONONLY0001'
CHARGE = 'ch_BountyForgeSIMULATIONONLY0001'
RECORDS = {
    '/v1/checkout/sessions/' + SESSION: {
        'id': SESSION, 'livemode': True, 'mode': 'payment', 'status': 'complete',
        'payment_status': 'paid', 'currency': 'usd', 'amount_total': 4900,
        'payment_intent': PAYMENT, 'payment_link': 'plink_BountyForgeSIMULATIONONLY0001',
        'metadata': {'bountyforge_service': 'python_bugfix_basic', 'contract_version': '1'}},
    '/v1/payment_intents/' + PAYMENT: {
        'id': PAYMENT, 'livemode': True, 'status': 'succeeded', 'currency': 'usd',
        'amount_received': 4900, 'amount': 4900, 'latest_charge': CHARGE},
    '/v1/charges/' + CHARGE: {
        'id': CHARGE, 'livemode': True, 'payment_intent': PAYMENT,
        'status': 'succeeded', 'paid': True, 'captured': True, 'refunded': False,
        'disputed': False, 'amount_refunded': 0, 'currency': 'usd',
        'amount': 4900, 'amount_captured': 4900},
}


def main():
    fd = os.open(sys.argv[1], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w', buffering=1) as log:
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def record(self):
                log.write(json.dumps({'method': self.command, 'path': self.path,
                                      'headers': dict(self.headers), 'peer': self.client_address[0]}) + '\n')

            def do_GET(self):
                self.record()
                if self.path not in RECORDS:
                    self.send_error(404)
                    return
                raw = json.dumps({'kind': 'phase8_provider_SIMULATOR', 'scenario': 'paid',
                                  'nonce': self.headers.get('X-BountyForge-Simulator-Nonce'),
                                  'record': RECORDS[self.path]}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                self.record()
                self.send_error(405)

        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            print(json.dumps({'port': server.server_port}), flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
