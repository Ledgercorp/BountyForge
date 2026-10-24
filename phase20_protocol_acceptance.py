"""Real contained SDK/gateway black-box QA with a labeled provider simulator.

This never runs a model, supplies a repair, invokes a verifier or counts accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import time
import uuid
from phase20_native_agent import ROOT,ENV,Rpc,public_file,execute,resources,validate_live_audit,assistant_response
from phase20_transport import model_command,sdk_command,IMAGE,MODEL_ID,PROVIDER_ID,MODEL_PROBE,validate_model_boundary
from phase17_isolation import PROBE,validate_observation
from phase17_sdk_bootstrap import extract_offline_runtime,RUNTIME_BIN
from phase19_native_binding import stage_native_cache
from phase19_sdk_acceptance import remove_container


def run(enabled=False,*,wheels=None):
    if enabled is not True:raise ValueError('EXPLICIT_PROTOCOL_SIMULATION_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    from bountyforge.profiled_qwen import COMPACT_SYSTEM
    from bountyforge.repair_engines import receipt_hash
    require_credential_free_host()
    record={'kind':'PHASE20_RECORDED_RESPONSE_PROTOCOL_QA','provider_mode':'SIMULATOR',
        'actual_model_requests':0,'model_generated_repairs':0,'private_execution_admitted':False,'commercial_admission':'NOT_ADMITTED'}
    began=time.monotonic();docker=shutil.which('docker')
    if not docker:raise RuntimeError('DOCKER_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='bf20-protocol-qa-') as temp:
        root=Path(temp);root.chmod(0o755);mw=root/'provider';sw=root/'sdk';assets=root/'empty-assets'
        for p in (mw,sw,assets):p.mkdir();p.chmod(0o755)
        for p in (mw,sw):public_file(p/'owned.txt','owned-development-only\n')
        public_file(mw/'model_service.py',(ROOT/'phase20_protocol_provider.py').read_bytes())
        public_file(mw/'phase20_model_service.py',(ROOT/'phase20_model_service.py').read_bytes())
        public_file(sw/'native-policy.mjs',(ROOT/'phase20_sdk_guard.mjs').read_bytes())
        public_file(sw/'agent-policy.json',json.dumps({'system':COMPACT_SYSTEM,'request_limit':2}))
        public_file(sw/'local.patch.yml',(ROOT/'phase17/hardened-sdk-minimal.patch.yml').read_bytes()+b'\n'+(ROOT/'phase20_local_provider.patch.yml').read_bytes())
        native=root/'native';extract_offline_runtime(wheels,native);stage_native_cache(native)
        mn='bf-p20-model-'+uuid.uuid4().hex[:16];sn='bf-p17-'+uuid.uuid4().hex[:16];model=sdk=None
        with (root/'provider.stderr').open('wb') as me,(root/'sdk.stderr').open('wb') as se:
            try:
                model=subprocess.Popen(model_command(docker,mw,mn,assets),stdin=subprocess.DEVNULL,stdout=me,stderr=me,env=ENV)
                for _ in range(30):
                    try:
                        execute(docker,mn,"import socket; s=socket.create_connection(('127.0.0.1',8081),timeout=1);s.close()",3);break
                    except RuntimeError:time.sleep(.2)
                else:raise RuntimeError('SIMULATOR_NOT_READY')
                record['provider_boundary']=validate_model_boundary(json.loads(execute(docker,mn,MODEL_PROBE)))
                cmd=sdk_command(docker,sw,sn,native,mn)
                cmd.insert(cmd.index(IMAGE),'--env=BOUNTYFORGE_LOCAL_NO_CREDENTIAL=local-no-credential')
                cmd[-5:]=[IMAGE,'/opt/harness/'+RUNTIME_BIN,'--profile','sdk-minimal','--patch','/workspace/local.patch.yml'];cmd.insert(cmd.index(IMAGE),'-i')
                sdk=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=se,bufsize=0,env=ENV)
                rpc=Rpc(sdk);record['initialize']=rpc.request('initialize',{'cwd':'/workspace','provider':PROVIDER_ID,'model':MODEL_ID,'maxTokens':150})
                try:rpc.request('bountyforge/unauthorized-execute',{})
                except RuntimeError as error:
                    if not str(error).startswith('SDK_RPC_ERROR_'):raise
                    record['unauthorized_method_rejected']=str(error)
                else:raise RuntimeError('UNAUTHORIZED_METHOD_ACCEPTED')
                session='owned-protocol-replay';rpc.request('session/working-directory/get',{'sessionId':session})
                record['sdk_boundary_before']=validate_observation(execute(docker,sn,PROBE))
                record['turns']=[]
                for _ in range(2):
                    offset=len(rpc.notifications)
                    rpc.request('session/prompt',{'sessionId':session,'contentBlocks':[{'type':'text','text':'Owned protocol replay only. No repair is measured.'}]})
                    rpc.request('session/wait',{'sessionId':session},timeout=30)
                    response=assistant_response(rpc.notifications[offset:])
                    if response!='{"':raise RuntimeError('RECORDED_SIMULATOR_RESPONSE_CHANGED')
                    record['turns'].append({'recorded_response_consumed':True,'boundary':validate_observation(execute(docker,sn,PROBE))})
                trace=json.loads(execute(docker,mn,"from pathlib import Path; print(Path('/tmp/bf20-model-trace.json').read_text())"))
                if trace['dispatched']!=2:raise RuntimeError('SIMULATED_REQUEST_COUNT_CHANGED')
                # Prove the real gateway refuses a third forwarding operation.
                test="import http.client,json; c=http.client.HTTPConnection('127.0.0.1',8081,timeout=3); b={'model':'bountyforge-qwen-1.5b','messages':[{'role':'user','content':'owned negative budget test'}],'stream':True,'max_tokens':150}; c.request('POST','/v1/chat/completions',json.dumps(b),{'Authorization':'Bearer local-no-credential'}); r=c.getresponse(); print(json.dumps({'status':r.status,'body':r.read(2048).decode()})); c.close()"
                denied=json.loads(execute(docker,mn,test))
                if denied['status']!=400 or 'BUDGET_EXHAUSTED' not in denied['body']:raise RuntimeError('GATEWAY_BUDGET_NOT_ENFORCED')
                negative_source="""import http.client,json
base={'model':'bountyforge-qwen-1.5b','messages':[{'role':'user','content':'owned negative test'}],'stream':True,'max_tokens':150}
cases=[('/v1/chat/completions',json.dumps({**base,'model':'unapproved'}),'local-no-credential'),
('/v1/chat/completions',json.dumps({**base,'tools':[{'type':'function'}]}),'local-no-credential'),
('/v1/chat/completions',json.dumps({**base,'max_tokens':151}),'local-no-credential'),
('/v1/files',json.dumps(base),'local-no-credential'),
('/v1/chat/completions',json.dumps(base),'unapproved-test-literal'),
('/v1/chat/completions','{"model":"one","model":"two"}','local-no-credential'),
('/v1/chat/completions','x'*12289,'local-no-credential')]
rows=[]
for path,body,key in cases:
 c=http.client.HTTPConnection('127.0.0.1',8081,timeout=3);c.request('POST',path,body,{'Authorization':'Bearer '+key});r=c.getresponse();rows.append({'status':r.status,'error':r.read(2048).decode()});c.close()
print(json.dumps(rows))
"""
                negatives=json.loads(execute(docker,mn,negative_source))
                if len(negatives)!=7 or any(n['status']!=400 for n in negatives):raise RuntimeError('GATEWAY_NEGATIVE_REQUEST_ACCEPTED')
                record['gateway_negative_requests']=negatives
                actual=json.loads(execute(docker,mn,"import http.client; c=http.client.HTTPConnection('127.0.0.1',8080,timeout=2); c.request('GET','/counter'); r=c.getresponse(); print(r.read(1024).decode());c.close()"))
                if actual['simulated_completions']!=2:raise RuntimeError('REJECTED_REQUEST_REACHED_BACKEND')
                record['third_request_denied_before_backend']=True;record['simulated_provider_requests']=2
                raw=(root/'sdk.stderr').read_bytes()
                audits=[json.loads(line.split(b' ',1)[1]) for line in raw.splitlines() if line.startswith((b'BOUNTYFORGE_LIVE_AUDIT ',b'BOUNTYFORGE_POST_TURN_AUDIT '))]
                if len(audits)!=3:raise RuntimeError('PRE_POST_TOOL_AUDIT_MISSING')
                record['tool_audits']=[validate_live_audit(a) for a in audits]
                expected_context='Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\n\nCurrent working directory: "/workspace".'
                for i,row in enumerate(trace['requests']):
                    messages=row['sdk_request']['messages']
                    if (len(messages)!=3+2*i or messages[2]!={'role':'user','content':expected_context}):
                        raise RuntimeError('UNEXPECTED_RUNTIME_CONTEXT_OR_PROMPT_HISTORY')
                record['required_runtime_context_preserved']=True
                record['request_message_counts']=[len(r['sdk_request']['messages']) for r in trace['requests']]
                record['sdk_resources']=resources(docker,sn);record['provider_resources']=resources(docker,mn)
                rpc.request('shutdown');sdk.stdin.close();sdk.wait(timeout=8)
                if sdk.returncode!=0:raise RuntimeError('SDK_NORMAL_SHUTDOWN_FAILED')
                record['shutdown_exit_code']=sdk.returncode
                record['sdk_stderr_sha256']=hashlib.sha256(raw).hexdigest()
            finally:
                for child,name in ((sdk,sn),(model,mn)):
                    if child is not None and child.poll() is None:child.kill();child.wait(timeout=5)
                    remove_container(docker,name)
                record['containers_absent_after_cleanup']=True
    record.update(status='PASSED',elapsed_seconds=round(time.monotonic()-began,3),additional_spending_usd=0)
    record['receipt_sha256']=receipt_hash(record)
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--admit-protocol-replay',action='store_true')
    p.add_argument('--wheel-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if not args.admit_protocol_replay:p.error('Explicit simulated protocol acceptance required')
    result=run(True,wheels=args.wheel_directory);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'actual_model_requests':0,'model_generated_repairs':0}));return 0


if __name__=='__main__':raise SystemExit(main())
