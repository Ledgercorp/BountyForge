import http.server
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
ROOT=Path(__file__).resolve().parents[1]


class RpcProcessTests(unittest.TestCase):
    def test_actual_process_uses_read_rpc_only_and_does_not_report_real_payment(self):
        methods=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));method=data['method'];methods.append(method)
                if method=='getTransaction':r={'slot':10,'transaction':{'signatures':['3'*88],'message':{'accountKeys':['4'*32,'2'*32]}},'meta':{'err':None,'preBalances':[100,0],'postBalances':[90,10]}}
                elif method=='getSignatureStatuses':r={'value':[{'slot':10,'err':None,'confirmationStatus':'finalized'}]}
                elif method=='getBalance':r={'context':{'slot':10},'value':10}
                else:self.send_error(400);return
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'jsonrpc':'2.0','id':data['id'],'result':r}).encode())
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            p=subprocess.run([sys.executable,'tests/crypto_rpc_probe.py',str(server.server_port)],cwd=ROOT,capture_output=True,text=True,timeout=10,
                env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(p.returncode,0,p.stderr);r=json.loads(p.stdout)
            self.assertEqual(methods,['getTransaction','getSignatureStatuses','getBalance'])
            self.assertEqual(r['receipt']['amount_base_units'],10);self.assertEqual(r['balance']['balance_base_units'],10)
            self.assertEqual(r['live_chain_payments_observed'],0);self.assertEqual(r['real_earnings_usd'],'0')
            self.assertTrue(r['simulated'])
        finally:server.shutdown();server.server_close();worker.join(timeout=2)
