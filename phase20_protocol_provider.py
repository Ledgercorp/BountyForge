"""PROTOCOL SIMULATOR ONLY. No model weights, inference or repair success.

Exercise the actual gateway against an owned fake native backend. The answer
is the recorded, rejected two-character fragment from the initial diagnostic.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer
sys.path.insert(0,'/workspace')
from phase20_model_service import Gateway,RequestBudget


class RecordedBackend(BaseHTTPRequestHandler):
    count=0
    def log_message(self,*args):pass
    def do_GET(self):
        raw=json.dumps({'simulated_completions':RecordedBackend.count}).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length','0')))
        if self.path in ('/apply-template','/tokenize'):
            raw=json.dumps({'prompt':'SIMULATED TOKENIZER INPUT'} if self.path=='/apply-template' else {'tokens':[1,2,3]}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        if self.path!='/v1/chat/completions':self.send_error(404);return
        RecordedBackend.count+=1
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
        for row in ({'id':'protocol-replay','object':'chat.completion.chunk','model':'bountyforge-qwen-1.5b',
                     'choices':[{'index':0,'delta':{'role':'assistant','content':'{"'},'finish_reason':None}]},
                    {'id':'protocol-replay','object':'chat.completion.chunk','model':'bountyforge-qwen-1.5b',
                     'choices':[{'index':0,'delta':{},'finish_reason':'length'}]}):
            self.wfile.write(('data: '+json.dumps(row)+'\n\n').encode());self.wfile.flush()
        self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush();self.close_connection=True


def main():
    backend=HTTPServer(('127.0.0.1',8080),RecordedBackend)
    threading.Thread(target=backend.serve_forever,daemon=True).start()
    gateway=HTTPServer(('127.0.0.1',8081),Gateway)
    gateway.config={'grammar':'root ::= "{"','request_limit':2,'pi_ai_context_guard_compat':True}
    gateway.budget=RequestBudget(2);gateway.rows=[]
    gateway.serve_forever()


if __name__=='__main__':main()
