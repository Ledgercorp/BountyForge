"""Owned sidecar: pinned llama.cpp plus bounded loopback-only SSE gateway.

Standalone stdlib code, copied into a read-only workspace. No verifier or
repository access. Configuration supplies only the approved grammar and budget.
"""
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import threading
import time

MODEL='bountyforge-qwen-1.5b'
TRACE=Path('/tmp/bf20-model-trace.json')


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('DUPLICATE_JSON_KEY')
        result[key]=value
    return result


def admit_request(path,raw,*,expected_model=MODEL):
    if expected_model not in (MODEL,'bountyforge-granite-3b'):raise ValueError('UNAPPROVED_MODEL_IDENTITY')
    if path!='/v1/chat/completions' or not 1<=len(raw)<=12288:raise ValueError('REQUEST_SCOPE')
    request=json.loads(raw,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))
    if type(request) is not dict or request.get('model')!=expected_model or request.get('stream') is not True:
        raise ValueError('MODEL_OR_STREAM_SCOPE')
    if request.get('tools') or request.get('tool_choice') not in (None,'none','auto'):
        raise ValueError('MODEL_TOOLS_FORBIDDEN')
    allowed={'model','messages','stream','stream_options','max_tokens','max_completion_tokens','temperature',
             'tools','tool_choice','store','top_p','frequency_penalty','presence_penalty','seed'}
    if set(request)-allowed:raise ValueError('REQUEST_FIELDS_REJECTED')
    limits=[request[k] for k in ('max_tokens','max_completion_tokens') if k in request]
    if not limits or any(type(n) is not int or not 1<=n<=150 for n in limits):raise ValueError('OUTPUT_TOKEN_LIMIT')
    messages=request.get('messages')
    if type(messages) is not list or not 1<=len(messages)<=16:raise ValueError('MESSAGE_LIMIT')
    if any(type(m) is not dict or m.get('role') not in ('system','user','assistant')
           or type(m.get('content')) is not str or set(m)-{'role','content'} for m in messages):
        raise ValueError('TEXT_ONLY_MESSAGES_REQUIRED')
    return {**request,'temperature':0,'stream_options':{'include_usage':True}}


class RequestBudget:
    def __init__(self,limit):
        if type(limit) is not int or not 1<=limit<=2:raise ValueError('REQUEST_BUDGET_LIMIT')
        self.limit=limit;self.dispatched=0;self.lock=threading.Lock()

    def reserve(self):
        with self.lock:
            if self.dispatched>=self.limit:raise ValueError('MODEL_REQUEST_BUDGET_EXHAUSTED')
            self.dispatched+=1


def restore_output_budget(request,prompt_tokens,*,compat=False):
    output=dict(request)
    # Pinned pi-ai reserves 4096 context tokens, clamping every 2048-context
    # route to one output token. This explicit shim restores the SDK's verified
    # 150-token contract only after the actual model tokenizer confirms room.
    # The model context, maximum output, validator and source scope never grow.
    if compat and max(output.get('max_tokens',0),output.get('max_completion_tokens',0))==1:
        if prompt_tokens>1898:raise ValueError('CONTEXT_LIMIT_EXCEEDED')
        for key in ('max_tokens','max_completion_tokens'):
            if key in output:output[key]=150
    return output


def native_json(path,body):
    connection=http.client.HTTPConnection('127.0.0.1',8080,timeout=45)
    try:
        connection.request('POST',path,json.dumps(body),{'Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read(65537)
        if response.status!=200 or len(raw)>65536:raise ValueError('PINNED_NATIVE_ENDPOINT_REJECTED')
        return json.loads(raw)
    finally:connection.close()


class Gateway(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'

    def log_message(self,*args):pass

    def setup(self):
        super().setup();self.connection.settimeout(45)

    def fail(self,code):
        raw=json.dumps({'error':{'message':code,'type':'bountyforge_boundary'}}).encode()
        self.send_response(400);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Connection','close')
        self.end_headers();self.wfile.write(raw);self.close_connection=True

    def do_GET(self):
        if self.path!='/v1/models':self.fail('FIXED_ROUTE_ONLY');return
        raw=json.dumps({'object':'list','data':[{'id':getattr(self.server,'model_id',MODEL),'object':'model','owned_by':'local-qwen' if getattr(self.server,'model_id',MODEL)==MODEL else 'local-granite'}]}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)

    def do_POST(self):
        identity=getattr(self.server,'model_id',MODEL)
        connection=None;started=time.monotonic();row={'model':identity,'completion_forwarded':False}
        try:
            if self.headers.get('Authorization')!='Bearer local-no-credential':raise ValueError('NO_PROVIDER_CREDENTIAL_ALLOWED')
            length=int(self.headers.get('Content-Length','-1'))
            if not 1<=length<=12288:raise ValueError('BODY_LIMIT')
            raw=self.rfile.read(length);body=admit_request(self.path,raw,expected_model=identity)
            row.update(sdk_request=json.loads(raw),sdk_request_sha256=hashlib.sha256(raw).hexdigest())
            template={'messages':body['messages'],'add_generation_prompt':True}
            if getattr(self.server,'disable_thinking',False):template['chat_template_kwargs']={'enable_thinking':False}
            rendered=native_json('/apply-template',template)
            prompt=rendered['prompt']
            tokens=native_json('/tokenize',{'content':prompt,'add_special':False,'parse_special':True})['tokens']
            row['rendered_prompt_tokens']=len(tokens)
            body=restore_output_budget(body,len(tokens),compat=self.server.config['pi_ai_context_guard_compat'])
            row['admitted_output_tokens']=max(body.get('max_tokens',0),body.get('max_completion_tokens',0))
            row['pi_ai_context_guard_compat']=self.server.config['pi_ai_context_guard_compat']
            if len(tokens)>1898 or len(tokens)+max(body.get('max_tokens',0),body.get('max_completion_tokens',0))>2048:
                raise ValueError('CONTEXT_LIMIT_EXCEEDED')
            self.server.budget.reserve()
            body['grammar']=self.server.config['grammar']
            if getattr(self.server,'disable_thinking',False):body['chat_template_kwargs']={'enable_thinking':False}
            connection=http.client.HTTPConnection('127.0.0.1',8080,timeout=45)
            row['completion_forwarded']=True
            connection.request('POST','/v1/chat/completions',json.dumps(body),{'Content-Type':'application/json'})
            upstream=connection.getresponse()
            if upstream.status!=200:raise ValueError('MODEL_HTTP_'+str(upstream.status))
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close')
            self.end_headers();self.close_connection=True
            content=[];captured=bytearray();done=False
            while True:
                remaining=45-(time.monotonic()-started)
                if remaining<=0:raise ValueError('MODEL_STREAM_DEADLINE')
                if connection.sock is not None:connection.sock.settimeout(remaining)
                line=upstream.readline(8193)
                if not line:break
                captured.extend(line)
                if len(line)>8192 or len(captured)>65536:raise ValueError('MODEL_STREAM_BUDGET')
                if line.startswith(b'data: '):
                    value=line[6:].strip()
                    if value==b'[DONE]':done=True
                    else:
                        data=json.loads(value)
                        if data.get('usage'):row['usage']=data['usage']
                        for choice in data.get('choices',[]):
                            delta=choice.get('delta',{})
                            if delta.get('tool_calls'):raise ValueError('MODEL_TOOL_CALL_REFUSED')
                            if delta.get('content'):content.append(delta['content'])
                            if choice.get('finish_reason'):row['finish_reason']=choice['finish_reason']
                self.wfile.write(line);self.wfile.flush()
                if done:break
            row.update(response=''.join(content),stream_done=done,response_sha256=hashlib.sha256(''.join(content).encode()).hexdigest())
        except (ValueError,KeyError,TypeError,OSError,http.client.HTTPException) as error:
            row['error']=str(error)[:100] if isinstance(error,ValueError) else type(error).__name__
            if not row['completion_forwarded']:
                try:self.fail(row['error'])
                except OSError:pass
        finally:
            if connection is not None:connection.close()
            row['seconds']=round(time.monotonic()-started,3)
            self.server.rows.append(row)
            temporary=TRACE.with_suffix('.tmp')
            temporary.write_text(json.dumps({'dispatched':self.server.budget.dispatched,'requests':self.server.rows},sort_keys=True))
            temporary.replace(TRACE)


def main():
    config=json.loads(Path('/workspace/model-config.json').read_text())
    if (set(config)!={'grammar','request_limit','pi_ai_context_guard_compat'} or type(config['grammar']) is not str
            or len(config['grammar'])>50000 or type(config['pi_ai_context_guard_compat']) is not bool):
        raise ValueError('FIXED_MODEL_CONFIG_REQUIRED')
    serve(config)


def serve(config,*,model_id=MODEL,disable_thinking=False):
    if ((model_id,disable_thinking) not in ((MODEL,False),('bountyforge-granite-3b',True))):
        raise ValueError('EXPLICIT_MODEL_EXECUTION_PROFILE_REQUIRED')
    resource.setrlimit(resource.RLIMIT_AS,(10*1024**3,10*1024**3))
    budget=RequestBudget(config['request_limit']);began=time.monotonic()
    log=open('/tmp/llama.log','wb')
    command=['/opt/qwen/llama-b11750/llama-server','-m','/opt/qwen/model.gguf',
        '--host','127.0.0.1','--port','8080','--alias',model_id,'-t','2','-c','2048','-np','1','--no-webui']
    if disable_thinking:command+=['--chat-template-kwargs','{"enable_thinking":false}']
    child=subprocess.Popen(command,
        stdout=log,stderr=log,env={'PATH':'/usr/local/bin:/usr/bin:/bin','LD_LIBRARY_PATH':'/opt/qwen/deps:/opt/qwen/llama-b11750'})
    server=None
    def terminate(*_):raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate)
    def watchdog():
        time.sleep(180)
        if child.poll() is None:child.kill()
        os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watchdog,daemon=True).start()
    try:
        for _ in range(60):
            if child.poll() is not None:raise RuntimeError('MODEL_PROCESS_EXITED')
            try:
                c=http.client.HTTPConnection('127.0.0.1',8080,timeout=1);c.request('GET','/health')
                r=c.getresponse();ready=r.status==200;r.read(1024);c.close()
                if ready:break
            except OSError:pass
            time.sleep(.5)
        else:raise RuntimeError('MODEL_LOAD_TIMEOUT')
        server=HTTPServer(('127.0.0.1',8081),Gateway);server.timeout=.5
        server.budget=budget;server.config=config;server.rows=[];server.model_id=model_id;server.disable_thinking=disable_thinking
        while child.poll() is None and time.monotonic()-began<180:server.handle_request()
    finally:
        if server:server.server_close()
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        log.close()


if __name__=='__main__':main()
