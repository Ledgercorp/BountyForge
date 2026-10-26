import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
KEY='sk-'+'x'*32

class ProcessHTTPTests(unittest.TestCase):
    def run_case(self,mode):
        observed=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                if self.path!='/user/balance':self.send_error(404);return
                data={'is_available':True,'balance_infos':[{'currency':'USD','total_balance':'22.88','granted_balance':'0.00','topped_up_balance':'22.88'}]}
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(data).encode())
            def do_POST(self):
                body=self.rfile.read(int(self.headers['Content-Length']))
                observed.append({'path':self.path,'secret_in_body':KEY.encode() in body,'authenticated':self.headers.get('Authorization')=='Bearer '+KEY})
                if mode=='redirect':
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:1/credential-sink');self.end_headers();return
                if mode=='timeout':time.sleep(0.4)
                value={'id':'simulated-response','model':'deepseek-v4-pro',
                    'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'{"changes":[{"line":3,"new":"return value"}]}'}}],
                    'usage':{'prompt_tokens':100,'completion_tokens':40,'total_tokens':140}}
                if mode=='tool':value['choices'][0]['message']['tool_calls']=[{'function':{'name':'bash'}}]
                self.send_response(200);self.end_headers()
                try:self.wfile.write(json.dumps(value).encode())
                except BrokenPipeError:pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as t:
                store=Path(t)/'private';store.mkdir(mode=0o700)
                p=subprocess.run([sys.executable,'tests/phase22_http_probe.py',str(server.server_port),str(store),mode],cwd=ROOT,
                                 capture_output=True,text=True,timeout=8,env={'PATH':'/usr/local/bin:/usr/bin:/bin','PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1'})
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertNotIn(KEY,p.stdout+p.stderr)
                r=json.loads(p.stdout);self.assertEqual(r['actual_live_provider_requests'],0)
                self.assertEqual(len(observed),1);self.assertTrue(observed[0]['authenticated']);self.assertFalse(observed[0]['secret_in_body'])
                return r
        finally:server.shutdown();server.server_close();worker.join(timeout=2)

    def test_real_process_http_response_and_persistent_usage(self):
        r=self.run_case('valid');self.assertEqual(r['status'],'RETURNED')
        self.assertEqual(r['budget']['committed_microusd'],291)
        self.assertEqual(r['budget']['unknown_requests'],0)

    def test_real_process_refuses_provider_tool_calls_after_accounting(self):
        r=self.run_case('tool');self.assertEqual(r['status'],'REJECTED')
        self.assertEqual(r['result']['diagnostic'],'MODEL_TOOL_CALL_REJECTED')
        self.assertEqual(r['budget']['committed_microusd'],291)

    def test_real_process_wall_deadline_retains_unknown_reservation(self):
        r=self.run_case('timeout');self.assertEqual(r['status'],'REJECTED')
        self.assertEqual(r['budget']['unknown_requests'],1)
        self.assertEqual(r['budget']['committed_microusd'],37848)

    def test_real_process_refuses_redirect_without_replaying_the_post(self):
        r=self.run_case('redirect');self.assertEqual(r['status'],'REJECTED')
        self.assertEqual(r['budget']['unknown_requests'],1)
