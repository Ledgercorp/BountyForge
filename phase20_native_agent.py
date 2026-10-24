"""Opt-in real native SDK -> contained local Qwen -> trusted owned verifier."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid

from phase17_isolation import IMAGE,PROBE,validate_observation
from phase17_sdk_bootstrap import extract_offline_runtime,RUNTIME_BIN,sanitized_boot_diagnostic
from phase19_native_binding import stage_native_cache
from phase19_sdk_acceptance import remove_container,FORBIDDEN
from phase20_transport import (stage_assets,model_command,sdk_command,MODEL_PROBE,validate_model_boundary,MODEL_ID,PROVIDER_ID)

ROOT=Path(__file__).resolve().parent
CONFIG_SHA='f0d86f4b3123709c9da432844e7f84eea0da30b8779a08f5abc873e6b903c040'
ENV={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp'}


def claim_arm(case_id,arm,*,root=None):
    """Reserve once before execution; interrupted/unknown usage never restores it."""
    from bountyforge.repair_engines import receipt_hash
    raw=(ROOT/'phase20_experiment.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CONFIG_SHA:raise ValueError('FROZEN_EXPERIMENT_CHANGED')
    spec=next((x for x in json.loads(raw)['tasks'] if x['case_id']==case_id),None)
    if spec is None or arm not in spec['arms']:raise ValueError('FROZEN_ARM_NOT_SELECTED')
    if case_id=='weighted-mix':
        history=json.loads((ROOT/'evidence/phase20/native-demo-v1.json').read_text())
        if (history.get('receipt_sha256')!='a6f8d04a1dc94680040b47b7f78f6e41f7bd81cef3e2c89e992982a3f99cd7f8'
                or receipt_hash(history)!=history['receipt_sha256']):raise ValueError('PRIOR_USAGE_IDENTITY_CHANGED')
        raise ValueError('FROZEN_ARM_ALREADY_COMPLETED')
    root=ROOT/'.bountyforge-phase20' if root is None else root
    if root.is_symlink():raise ValueError('CLAIM_STORE_REJECTED')
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode & 0o077:raise ValueError('PRIVATE_CLAIM_STORE_REQUIRED')
    path=root/(case_id+'.'+arm+'.claim')
    try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except FileExistsError:raise ValueError('FROZEN_ARM_ALREADY_RESERVED') from None
    try:
        os.write(fd,json.dumps({'experiment_sha256':CONFIG_SHA,'case_id':case_id,'arm':arm,'reserved':spec['arms'][arm]}).encode())
        os.fsync(fd)
    finally:os.close(fd)
    return spec['arms'][arm]


def validate_live_audit(record):
    if (type(record) is not dict or record.get('tool_names')!=[] or record.get('credential_names_present')!=[]
            or record.get('sdk_session_persistence')!='MEMORY_ONLY'
            or record.get('mcp_resources_service_present') is not False or type(record.get('refusals')) is not list
            or [r.get('tool') for r in record['refusals']]!=list(FORBIDDEN)
            or any(r.get('available') is not False or r.get('invoked') is not True or r.get('unknown_tool') is not True for r in record['refusals'])):
        raise ValueError('LIVE_CAPABILITY_REFUSALS_UNCONFIRMED')
    return record


def assistant_response(notifications):
    for row in reversed(notifications):
        if row.get('method')!='session.event':continue
        event=row.get('params',{}).get('event',{})
        if event.get('type')!='assistant/message':continue
        data=event.get('data',{});content=data.get('message',data).get('content',[])
        if any(b.get('type')!='text' for b in content):raise ValueError('SDK_TOOL_RESPONSE_REFUSED')
        return ''.join(b.get('text','') for b in content)
    return ''


class Rpc:
    def __init__(self,child):
        self.child=child;self.buffer=b'';self.notifications=[];self.total_bytes=0;self.counter=0

    def request(self,method,params=None,timeout=20):
        self.counter+=1;identity='bf20-'+str(self.counter)
        self.child.stdin.write((json.dumps({'jsonrpc':'2.0','id':identity,'method':method,'params':params})+'\n').encode())
        self.child.stdin.flush();deadline=time.monotonic()+timeout
        with selectors.DefaultSelector() as selected:
            selected.register(self.child.stdout,selectors.EVENT_READ)
            while time.monotonic()<deadline:
                if b'\n' not in self.buffer:
                    if not selected.select(min(1,max(0,deadline-time.monotonic()))):continue
                    block=os.read(self.child.stdout.fileno(),4096)
                    if not block:raise RuntimeError('SDK_RPC_STREAM_CLOSED')
                    self.total_bytes+=len(block);self.buffer+=block
                    if self.total_bytes>512*1024 or len(self.buffer)>65536:raise RuntimeError('SDK_RPC_OUTPUT_BUDGET')
                while b'\n' in self.buffer:
                    raw,self.buffer=self.buffer.split(b'\n',1);row=json.loads(raw)
                    if row.get('id')==identity:
                        if 'error' in row:raise RuntimeError('SDK_RPC_ERROR_'+str(row['error'].get('code')))
                        return row.get('result')
                    if 'id' in row:raise RuntimeError('UNEXPECTED_SDK_ORIGINATED_REQUEST')
                    self.notifications.append(row)
        raise RuntimeError('SDK_RPC_DEADLINE')


def execute(docker,name,source,timeout=20):
    completed=subprocess.run([docker,'exec',name,'python','-I','-B','-c',source],capture_output=True,timeout=timeout,env=ENV)
    if completed.returncode!=0 or len(completed.stdout)>128*1024:raise RuntimeError('CONTAINED_OBSERVATION_FAILED')
    return completed.stdout.decode()


def resources(docker,name):
    source="import pathlib,json; p=pathlib.Path('/sys/fs/cgroup'); print(json.dumps({n:(p/n).read_text().strip() if (p/n).exists() else None for n in ('memory.peak','memory.max','cpu.max','cpu.stat','pids.peak','pids.max')}))"
    return json.loads(execute(docker,name,source))


def public_file(path,content):
    path.write_bytes(content if isinstance(content,bytes) else content.encode());path.chmod(0o444)


def model_trace(docker,name):
    return json.loads(execute(docker,name,"import pathlib; p=pathlib.Path('/tmp/bf20-model-trace.json'); print(p.read_text() if p.exists() else '{\"dispatched\":0,\"requests\":[]}')"))


def run_case(spec,assets,native,workroot,docker,*,model_free=False):
    from bountyforge.repair_engines import RepairService,receipt_hash
    from bountyforge.repair_intelligence import compact_model_prompt
    from bountyforge.profiled_qwen import COMPACT_SYSTEM
    from bountyforge.qwen_statement_contract import statement_schema
    from bountyforge.statement_grammar import statement_grammar
    from deepseek_owned_bridge import verify_owned_harness_response
    from deepseek_harness_handoff import HarnessHandoffRejected
    began=time.monotonic();service=RepairService();task=service.prepare(spec['case_id'],'CODEX_AGENT')
    if any(task[k]!=spec[k] for k in ('source_sha256','tests_sha256')):raise ValueError('FROZEN_TASK_CHANGED')
    limit=spec['arms']['NATIVE_SDK']
    if not model_free and claim_arm(spec['case_id'],'NATIVE_SDK')!=limit:raise ValueError('FROZEN_ARM_BUDGET_CHANGED')
    record={'case_id':spec['case_id'],'arm':'NATIVE_SDK','provider':PROVIDER_ID,'model':MODEL_ID,
        'model_sha256':'cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046',
        'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,'task':task,'attempts':[],
        'candidate_author':'SDK_DRIVEN_QWEN_LOCAL','codex_authored_candidates':0,'status':'BLOCKED',
        'submission_capability':'CODEX_AGENT','submission_capability_attests_authorship':False}
    modelwork=workroot/'model';sdkwork=workroot/'sdk'
    for directory in (modelwork,sdkwork):
        directory.mkdir();directory.chmod(0o755);public_file(directory/'owned.txt','owned-development-only\n')
    schema=statement_schema(task['source'],task['edit_units'])
    kinds={unit['line']:unit['kind'] for unit in task['edit_units']}
    for entry in schema['properties']['changes']['items']['anyOf']:
        entry['x-owned-unit-kind']=kinds[entry['properties']['line']['const']]
    grammar=statement_grammar(schema,compact=True)
    public_file(modelwork/'model-config.json',json.dumps({'grammar':grammar,'request_limit':limit,'pi_ai_context_guard_compat':True}))
    public_file(modelwork/'model_service.py',(ROOT/'phase20_model_service.py').read_bytes())
    public_file(sdkwork/'agent-policy.json',json.dumps({'system':COMPACT_SYSTEM,'request_limit':limit}))
    public_file(sdkwork/'native-policy.mjs',(ROOT/'phase20_sdk_guard.mjs').read_bytes())
    public_file(sdkwork/'local.patch.yml',(ROOT/'phase17/hardened-sdk-minimal.patch.yml').read_bytes()+b'\n'+(ROOT/'phase20_local_provider.patch.yml').read_bytes())
    modelname='bf-p20-model-'+uuid.uuid4().hex[:16];sdkname='bf-p17-'+uuid.uuid4().hex[:16]
    model=None;sdk=None;record['model_container_name']=modelname;record['sdk_container_name']=sdkname
    with (workroot/'model.stderr').open('wb') as modelerr,(workroot/'sdk.stderr').open('wb') as sdkerr:
        try:
            cmd=model_command(docker,modelwork,modelname,assets)
            model=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=modelerr,stderr=modelerr,env=ENV,start_new_session=True)
            ready=time.monotonic()+45
            while time.monotonic()<ready:
                if model.poll() is not None:raise RuntimeError('MODEL_SIDECAR_EXITED')
                try:
                    discovery=json.loads(execute(docker,modelname,"import urllib.request; print(urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8081/v1/models',timeout=1).read(2048).decode())",timeout=3))
                    if [x['id'] for x in discovery['data']]!=[MODEL_ID]:raise ValueError('LOCAL_MODEL_DISCOVERY_CHANGED')
                    record['discovered_models']=discovery;break
                except (RuntimeError,ValueError,subprocess.TimeoutExpired):time.sleep(.5)
            else:raise RuntimeError('MODEL_SIDECAR_LOAD_TIMEOUT')
            record['model_boundary_before']=validate_model_boundary(json.loads(execute(docker,modelname,MODEL_PROBE)))
            cmd=sdk_command(docker,sdkwork,sdkname,native,modelname)
            cmd.insert(cmd.index(IMAGE),'--env=BOUNTYFORGE_LOCAL_NO_CREDENTIAL=local-no-credential')
            cmd[-5:]=[IMAGE,'/opt/harness/'+RUNTIME_BIN,'--profile','sdk-minimal','--patch','/workspace/local.patch.yml']
            cmd.insert(cmd.index(IMAGE),'-i')
            sdk=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=sdkerr,env=ENV,bufsize=0,start_new_session=True)
            rpc=Rpc(sdk)
            initial=rpc.request('initialize',{'cwd':'/workspace','provider':PROVIDER_ID,'model':MODEL_ID,'maxTokens':150})
            if initial.get('serverInfo',{}).get('name')!='deepseek-harness-sdk-runtime':raise ValueError('SDK_IDENTITY_CHANGED')
            record['initialize']=initial;session='bountyforge-owned-'+task['task_id']
            rpc.request('session/working-directory/get',{'sessionId':session})
            raw=(workroot/'sdk.stderr').read_bytes()
            audits=[json.loads(line.split(b' ',1)[1]) for line in raw.splitlines() if line.startswith(b'BOUNTYFORGE_LIVE_AUDIT ')]
            if len(audits)!=1:raise ValueError('LIVE_CAPABILITY_AUDIT_MISSING')
            record['live_audit']=validate_live_audit(audits[0])
            record['sdk_boundary_before']=validate_observation(execute(docker,sdkname,PROBE))
            previous=None
            for _ in range(0 if model_free else limit):
                before=model_trace(docker,modelname)['dispatched']
                if before>=limit:break
                prompt=compact_model_prompt(task,previous)
                offset=len(rpc.notifications);turn=time.monotonic()
                rpc.request('session/prompt',{'sessionId':session,'contentBlocks':[{'type':'text','text':prompt}]})
                rpc.request('session/wait',{'sessionId':session},timeout=65)
                notifications=rpc.notifications[offset:];response=assistant_response(notifications)
                trace=model_trace(docker,modelname)
                if not trace['requests'] or not response or response.strip()!=trace['requests'][-1].get('response','').strip():
                    raise ValueError('SDK_CONSUMED_RESPONSE_UNCONFIRMED')
                if len(response.encode())>3000:raise ValueError('SDK_CANDIDATE_BUDGET_EXCEEDED')
                record['sdk_boundary_after']=json.loads(execute(docker,sdkname,PROBE))
                validate_observation(json.dumps(record['sdk_boundary_after']))
                post_audits=[json.loads(line.split(b' ',1)[1]) for line in (workroot/'sdk.stderr').read_bytes().splitlines()
                    if line.startswith(b'BOUNTYFORGE_POST_TURN_AUDIT ')]
                if len(post_audits)!=len(record['attempts'])+1:raise ValueError('POST_TURN_AUDIT_MISSING')
                post_audit=validate_live_audit(post_audits[-1])
                attempt={'sdk_final_response':response,'sdk_response_sha256':hashlib.sha256(response.encode()).hexdigest(),
                    'post_turn_tool_audit':post_audit,
                    'sdk_consumed_model_response':True,'turn_seconds':round(time.monotonic()-turn,3),
                    'sdk_events':[n['params']['event'] for n in notifications if n.get('method')=='session.event'
                        and n.get('params',{}).get('event',{}).get('type') in ('assistant/message','request/header','request/context','turn/end')]}
                record['attempts'].append(attempt)
                try:
                    attempt['verification']=verify_owned_harness_response(service,task,response,allow_owned_verification=True)
                except HarnessHandoffRejected as error:
                    attempt['handoff_rejection']=str(error)
                    previous={'proposal':response,'outcome':'SOURCE_REJECTED','diagnostic':str(error)}
                    continue
                previous=attempt['verification']['owned_verifier_receipt']
                if previous['state']!='REVISION_REQUIRED':break
                task=copy.deepcopy(service._get(task['task_id'],previous['revision'],'CODEX_AGENT')['public'])
            record['model_trace']=model_trace(docker,modelname)
            record['sdk_boundary_after']=json.loads(execute(docker,sdkname,PROBE))
            validate_observation(json.dumps(record['sdk_boundary_after']))
            record['model_boundary_after']=validate_model_boundary(json.loads(execute(docker,modelname,MODEL_PROBE)))
            record['sdk_resources']=resources(docker,sdkname);record['model_resources']=resources(docker,modelname)
            rpc.request('shutdown');sdk.stdin.close();sdk.wait(timeout=8)
            if sdk.returncode!=0:raise RuntimeError('SDK_SHUTDOWN_EXIT_REJECTED')
            record.update(shutdown_confirmed=True,sdk_exit_code=sdk.returncode,status='COMPLETED')
        except (RuntimeError,ValueError,OSError,subprocess.SubprocessError,KeyError) as error:
            record['failure']=str(error)[:150] if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__
            try:record['model_trace']=model_trace(docker,modelname)
            except (RuntimeError,OSError,subprocess.SubprocessError,ValueError):pass
        finally:
            for child,name in ((sdk,sdkname),(model,modelname)):
                if child is not None and child.poll() is None:child.kill();child.wait(timeout=5)
                remove_container(docker,name)
            record['containers_absent_after_cleanup']=True
    raw=(workroot/'sdk.stderr').read_bytes();record['sdk_diagnostic']=sanitized_boot_diagnostic(raw)
    record['sdk_request_events']=[json.loads(line.split(b' ',1)[1]) for line in raw.splitlines() if line.startswith(b'BOUNTYFORGE_SDK_REQUEST ')]
    record['model_requests']=record.get('model_trace',{}).get('dispatched',0)
    record['sdk_diagnostic']['model_calls']=record['model_requests']
    if model_free:record['arm']='MODEL_FREE_BOUNDARY_DIAGNOSIS'
    record['verified_repairs']=int(any(a.get('verification',{}).get('independently_verified_owned_development') is True for a in record['attempts']))
    record['elapsed_seconds']=round(time.monotonic()-began,3)
    record.update(commercial_admission='NOT_ADMITTED',additional_spending_usd=0,private_execution_admitted=False)
    record['receipt_sha256']=receipt_hash(record)
    return record


def run_experiment(admitted=False,*,wheels=None,stage='demo',case_id=None):
    if admitted is not True:raise ValueError('EXPLICIT_NATIVE_QWEN_ADMISSION_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    from bountyforge.repair_engines import receipt_hash
    require_credential_free_host()
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise ValueError('LINUX_X64_REQUIRED')
    config=(ROOT/'phase20_experiment.json').read_bytes()
    if hashlib.sha256(config).hexdigest()!=CONFIG_SHA:raise ValueError('FROZEN_EXPERIMENT_CHANGED')
    plan=json.loads(config)
    if stage not in ('demo','sdk-case'):raise ValueError('EXPERIMENT_STAGE_NOT_ADMITTED')
    spec=plan['tasks'][0] if stage=='demo' else next((x for x in plan['tasks'][1:] if x['case_id']==case_id),None)
    if spec is None:raise ValueError('FROZEN_TASK_NOT_SELECTED')
    cpus=os.cpu_count() or 0
    memory=int(next(r.split()[1] for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:')))
    if cpus<2 or memory<4*1024**2 or shutil.disk_usage(Path.home()).free<2*1024**3:raise ValueError('NATIVE_PAIR_CAPACITY_UNAVAILABLE')
    docker=shutil.which('docker')
    if not docker:raise RuntimeError('DOCKER_UNAVAILABLE')
    began=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='bf20-native-') as temp:
        root=Path(temp);root.chmod(0o755)
        assets=root/'assets';asset_proof=stage_assets(assets,Path.home()/'.cache/bountyforge')
        native=root/'native';archives=extract_offline_runtime(wheels,native);stage_native_cache(native)
        work=root/'case';work.mkdir();work.chmod(0o755)
        case=run_case(spec,assets,native,work,docker)
        result={'kind':plan['kind'],'stage':stage,'experiment_sha256':CONFIG_SHA,'assets':asset_proof,'sdk_archives':archives,
            'cases':[case],'status':'PASSED' if case['status']=='COMPLETED' and case['verified_repairs']==1 else 'NOT_VERIFIED',
            'independent_evaluation':False,'elapsed_seconds':round(time.monotonic()-began,3),'commercial_admission':'NOT_ADMITTED',
            'additional_spending_usd':0,'provider_credentials_supplied':False}
    result['receipt_sha256']=receipt_hash(result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admit-native-qwen',action='store_true');parser.add_argument('--wheel-directory',type=Path,required=True)
    parser.add_argument('--stage',choices=('demo','sdk-case'),default='demo')
    parser.add_argument('--case-id',choices=('optional-setting','reading-groups','reserve-release'))
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    if not args.admit_native_qwen:parser.error('Explicit native local inference admission required')
    result=run_experiment(True,wheels=args.wheel_directory,stage=args.stage,case_id=args.case_id)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'cases':[{'case_id':c['case_id'],'status':c['status'],'failure':c.get('failure'),
        'model_requests':c['model_requests'],'verified_repairs':c['verified_repairs']} for c in result['cases']]}))
    return 0 if result['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
