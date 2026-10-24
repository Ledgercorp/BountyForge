"""Explicit frozen owned comparison; no paid/network provider or shell tools."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from phase20_native_agent import (ENV,Rpc,assistant_response,execute,model_trace,public_file,resources,validate_live_audit)
from phase20_transport import stage_assets,model_command,sdk_command,MODEL_PROBE,validate_model_boundary,IMAGE,MODEL_ID,PROVIDER_ID
from phase17_isolation import PROBE,validate_observation
from phase17_sdk_bootstrap import extract_offline_runtime,RUNTIME_BIN
from phase19_native_binding import stage_native_cache
from phase19_sdk_acceptance import remove_container
from phase21_reasoning import SYSTEM,parse_candidate,repair_prompt,output_grammar
from bountyforge.repair_engines import RepairService,receipt_hash
from bountyforge.model_profiles import profile_spec

ROOT=Path(__file__).resolve().parent
CASES=('shipment-total','cache-refresh','parameter-pairs','inventory-adjustments')
ARMS=('EXTERNAL_BASE','SDK_BASE','SDK_DIAG')
ALL_ARMS=(*ARMS,'GRANITE_DIAG')
RESULTS=ROOT/'evidence/phase21/results'
CLAIMS=ROOT/'.bountyforge-phase21'


def install_stop_handler():
    def stopped(signum,_frame):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,stopped)


def claim(case,arm,*,root=CLAIMS,history=RESULTS):
    if case not in CASES or arm not in ALL_ARMS:raise ValueError('UNAUTHORIZED_EXPERIMENT_ARM')
    if (history/(case+'--'+arm+'.json')).exists():raise ValueError('RECORDED_ARM_CLOSED')
    if root.is_symlink():raise ValueError('PRIVATE_STORE_REQUIRED')
    root.mkdir(mode=0o700,exist_ok=True,parents=True)
    if root.stat().st_uid!=os.getuid() or root.stat().st_mode&0o077:raise ValueError('PRIVATE_STORE_REQUIRED')
    try:fd=os.open(root/(case+'--'+arm+'.claim'),os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('ARM_ALREADY_RESERVED') from None
    try:os.write(fd,b'two requests reserved; interruption never refunds\n');os.fsync(fd)
    finally:os.close(fd)


def load_plan(expected,selection='QWEN_COMPARISON'):
    if selection not in ('QWEN_COMPARISON','GRANITE_TRIAL'):raise ValueError('FROZEN_SELECTION_REQUIRED')
    raw=(ROOT/('phase21_experiment.json' if selection=='QWEN_COMPARISON' else 'phase21_stronger_experiment.json')).read_bytes()
    if type(expected) is not str or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('PINNED_EXPERIMENT_REQUIRED')
    plan=json.loads(raw)
    selected=list(ARMS) if selection=='QWEN_COMPARISON' else ['GRANITE_DIAG']
    if (plan['case_ids']!=list(CASES) or plan['arms']!=selected or plan['requests_per_arm_task']!=2
            or plan['maximum_model_requests']!=len(CASES)*len(selected)*2 or plan['context_tokens']!=2048 or plan['output_tokens']!=150):
        raise ValueError('EXPERIMENT_BUDGET_CHANGED')
    for name,digest in plan['frozen_files'].items():
        path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('FROZEN_IMPLEMENTATION_OR_TASK_CHANGED')
    return plan


def admit_capacity(cpu_max,memory_max,memory_current,model_bytes):
    raw_quota,raw_period=cpu_max.split();period=int(raw_period)
    quota=int(raw_quota) if raw_quota!='max' else len(os.sched_getaffinity(0))*period
    required=model_bytes+192*1024**2+512*1024**2
    if period<=0 or quota<2*period or memory_max-memory_current<required:
        raise ValueError('INDEPENDENT_CGROUP_CAPACITY_UNAVAILABLE')
    return {'admitted':True,'cpu_max':cpu_max,'memory_max':memory_max,
        'memory_current':memory_current,'model_limit':model_bytes,'required_headroom':required}


def capacity(model_bytes):
    group=Path('/sys/fs/cgroup')
    maximum=(group/'memory.max').read_text().strip();current=int((group/'memory.current').read_text())
    if maximum=='max':
        available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        result=admit_capacity((group/'cpu.max').read_text().strip(),available,0,model_bytes)
        result['headroom_basis']='HOST_MEM_AVAILABLE_WITHOUT_OUTER_CGROUP_LIMIT'
        return result
    result=admit_capacity((group/'cpu.max').read_text().strip(),int(maximum),current,model_bytes)
    result['headroom_basis']='OUTER_CGROUP_LIMIT_MINUS_CURRENT'
    return result


def process_memory(docker,name):
    source="""import pathlib,json
rows=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes().split(b'\\0')
  if p.name!='1' and not cmd[0].startswith(b'/opt/qwen/llama-b11750/llama'):continue
  d=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
  rows.append({'pid':int(p.name),'role':'container_main' if p.name=='1' else 'llama', 'peak_rss_bytes':int(d.get('VmHWM','0 kB').split()[0])*1024})
 except (OSError,ValueError):pass
print(json.dumps(rows))
"""
    return json.loads(execute(docker,name,source))


def run_arm(case,arm,assets,native,work,docker,experiment_sha):
    from bountyforge.profiled_qwen import COMPACT_SYSTEM
    from bountyforge.repair_intelligence import compact_model_prompt,revision_proposal
    from deepseek_owned_bridge import verify_owned_harness_response
    from deepseek_harness_handoff import HarnessHandoffRejected
    granite=arm=='GRANITE_DIAG';profile='GRANITE42_3B' if granite else 'QWEN_1_5B'
    model_id='bountyforge-granite-3b' if granite else MODEL_ID
    provider_id='bountyforge-local-granite' if granite else PROVIDER_ID
    probe=MODEL_PROBE.replace('3221225472','5368709120') if granite else MODEL_PROBE
    capacity_proof=capacity((5 if granite else 3)*1024**3)
    claim(case,arm)
    began=time.monotonic();service=RepairService(owned_quality=True);task=service.prepare(case,'CODEX_AGENT')
    record={'kind':'PHASE21_OWNED_MODEL_ARM','case_id':case,'arm':arm,'experiment_sha256':experiment_sha,
        'task':task,'preparation_seconds':round(time.monotonic()-began,3),'attempts':[],
        'model_profile':profile,'model_sha256':profile_spec(profile)['sha256'],
        'provider_id':provider_id if arm!='EXTERNAL_BASE' else 'bountyforge-external-local','model_id':model_id,
        'candidate_author':('QWEN_LOCAL_EXTERNAL' if arm=='EXTERNAL_BASE' else ('SDK_DRIVEN_GRANITE_LOCAL' if granite else 'SDK_DRIVEN_QWEN_LOCAL')),
        'codex_authored_candidates':0,'submission_capability_attests_authorship':False,
        'classification':'EXPOSED_OWNED_DEVELOPMENT','independent_evaluation':False,'status':'BLOCKED',
        'capacity_admission':capacity_proof}
    modelwork=work/'model';sdkwork=work/'sdk'
    for p in (modelwork,sdkwork):p.mkdir();p.chmod(0o755);public_file(p/'owned.txt','owned-development-only\n')
    diagnostic=arm in ('SDK_DIAG','GRANITE_DIAG');is_sdk=arm!='EXTERNAL_BASE'
    public_file(modelwork/'model-config.json',json.dumps({'grammar':output_grammar(task,diagnostic),'request_limit':2,'pi_ai_context_guard_compat':is_sdk}))
    public_file(modelwork/'model_service.py',(ROOT/('phase21_model_service.py' if granite else 'phase20_model_service.py')).read_bytes())
    if granite:public_file(modelwork/'phase20_model_service.py',(ROOT/'phase20_model_service.py').read_bytes())
    public_file(modelwork/'external_client.py',(ROOT/'phase20_external_client.py').read_bytes())
    public_file(sdkwork/'agent-policy.json',json.dumps({'system':SYSTEM if diagnostic else COMPACT_SYSTEM,'request_limit':2,'provider':provider_id,'model':model_id}))
    public_file(sdkwork/'native-policy.mjs',(ROOT/'phase20_sdk_guard.mjs').read_bytes())
    public_file(sdkwork/'local.patch.yml',(ROOT/'phase17/hardened-sdk-minimal.patch.yml').read_bytes()+b'\n'+(ROOT/('phase21_granite_provider.patch.yml' if granite else 'phase20_local_provider.patch.yml')).read_bytes())
    modelname='bf-p20-model-'+uuid.uuid4().hex[:16];sdkname='bf-p17-'+uuid.uuid4().hex[:16]
    model=sdk=None
    with (work/'model.stderr').open('wb') as me,(work/'sdk.stderr').open('wb') as se:
        try:
            model=subprocess.Popen(model_command(docker,modelwork,modelname,assets,profile=profile),stdin=subprocess.DEVNULL,stdout=me,stderr=me,env=ENV)
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if model.poll() is not None:raise RuntimeError('MODEL_SIDECAR_EXITED')
                try:execute(docker,modelname,"import socket;s=socket.create_connection(('127.0.0.1',8081),timeout=1);s.close()",3);break
                except (RuntimeError,subprocess.TimeoutExpired):time.sleep(.5)
            else:raise RuntimeError('MODEL_LOAD_TIMEOUT')
            record['model_boundary_before']=validate_model_boundary(json.loads(execute(docker,modelname,probe)))
            if is_sdk:
                cmd=sdk_command(docker,sdkwork,sdkname,native,modelname);cmd.insert(cmd.index(IMAGE),'--env=BOUNTYFORGE_LOCAL_NO_CREDENTIAL=local-no-credential')
                cmd[-5:]=[IMAGE,'/opt/harness/'+RUNTIME_BIN,'--profile','sdk-minimal','--patch','/workspace/local.patch.yml'];cmd.insert(cmd.index(IMAGE),'-i')
                sdk=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=se,bufsize=0,env=ENV)
                rpc=Rpc(sdk);record['initialize']=rpc.request('initialize',{'cwd':'/workspace','provider':provider_id,'model':model_id,'maxTokens':150})
                session='owned-quality-'+task['task_id'];rpc.request('session/working-directory/get',{'sessionId':session})
                record['sdk_boundary_before']=validate_observation(execute(docker,sdkname,PROBE))
            previous=None
            for number in range(1,3):
                prompt=repair_prompt(task,previous) if diagnostic else compact_model_prompt(task,previous)
                turn=time.monotonic()
                if is_sdk:
                    offset=len(rpc.notifications)
                    rpc.request('session/prompt',{'sessionId':session,'contentBlocks':[{'type':'text','text':prompt}]})
                    rpc.request('session/wait',{'sessionId':session},timeout=65)
                    notices=rpc.notifications[offset:];response=assistant_response(notices)
                    validate_observation(execute(docker,sdkname,PROBE))
                else:
                    messages=[{'role':'system','content':COMPACT_SYSTEM},{'role':'user','content':prompt}]
                    result=subprocess.run([docker,'exec','-i',modelname,'python','-I','-B','/workspace/external_client.py'],
                        input=json.dumps(messages).encode(),capture_output=True,timeout=65,env=ENV)
                    if result.returncode or len(result.stdout)>65536:raise RuntimeError('EXTERNAL_STREAM_REJECTED')
                    response=json.loads(result.stdout)['response']
                trace=model_trace(docker,modelname)
                if (trace['dispatched']!=number or not trace['requests'] or trace['requests'][-1].get('response')!=response
                        or trace['requests'][-1].get('stream_done') is not True):raise ValueError('MODEL_RESPONSE_ROUTE_UNCONFIRMED')
                attempt={'attempt':number,'response':response,'response_sha256':hashlib.sha256(response.encode()).hexdigest(),
                    'request_prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'turn_seconds':round(time.monotonic()-turn,3),
                    'sdk_consumed_model_response':is_sdk}
                if is_sdk:
                    attempt['sdk_events']=[n['params']['event'] for n in notices if n.get('method')=='session.event'
                        and n.get('params',{}).get('event',{}).get('type') in ('assistant/message','request/header','turn/end')]
                    audits=[json.loads(line.split(b' ',1)[1]) for line in (work/'sdk.stderr').read_bytes().splitlines()
                        if line.startswith(b'BOUNTYFORGE_POST_TURN_AUDIT ')]
                    if len(audits)!=number:raise ValueError('POST_TURN_TOOL_AUDIT_MISSING')
                    attempt['tool_audit']=validate_live_audit(audits[-1])
                record['attempts'].append(attempt)
                try:
                    proposal=response
                    if diagnostic:attempt['diagnosis'],proposal=parse_candidate(response,task)
                    effective,retained=revision_proposal(previous,proposal)
                    attempt.update(effective_proposal=effective,retained_anchors=retained)
                    before=time.monotonic();attempt['verification']=verify_owned_harness_response(service,task,effective,allow_owned_verification=True)
                    attempt['verification_seconds']=round(time.monotonic()-before,3)
                    previous=attempt['verification']['owned_verifier_receipt']
                except (HarnessHandoffRejected,ValueError) as error:
                    attempt['rejection']=str(error)[:160]
                    previous={'outcome':'SOURCE_REJECTED','proposal':response,'diagnostic':str(error)[:160]}
                    continue
                if previous['state']!='REVISION_REQUIRED':break
                task=copy.deepcopy(service._get(task['task_id'],previous['revision'],'CODEX_AGENT')['public'])
            record['model_boundary_after']=validate_model_boundary(json.loads(execute(docker,modelname,probe)))
            record['model_resources']=resources(docker,modelname);record['model_process_memory']=process_memory(docker,modelname)
            if is_sdk:
                record['sdk_boundary_after']=validate_observation(execute(docker,sdkname,PROBE))
                record['sdk_resources']=resources(docker,sdkname);record['sdk_process_memory']=process_memory(docker,sdkname)
                audits=[json.loads(line.split(b' ',1)[1]) for line in (work/'sdk.stderr').read_bytes().splitlines() if line.startswith(b'BOUNTYFORGE_LIVE_AUDIT ')]
                if len(audits)!=1:raise ValueError('STARTUP_TOOL_AUDIT_MISSING')
                record['startup_tool_audit']=validate_live_audit(audits[0])
                rpc.request('shutdown');sdk.stdin.close();sdk.wait(timeout=8)
                if sdk.returncode!=0:raise ValueError('SDK_SHUTDOWN_FAILED')
                record['sdk_exit_code']=sdk.returncode
            record['status']='COMPLETED'
        except (RuntimeError,ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
            record['failure']=str(error)[:200]
        finally:
            try:record['model_trace']=model_trace(docker,modelname)
            except (RuntimeError,ValueError,OSError,subprocess.SubprocessError):pass
            for child,name in ((sdk,sdkname),(model,modelname)):
                if child is not None and child.poll() is None:child.kill();child.wait(timeout=5)
                remove_container(docker,name)
            record['cleanup_confirmed']=True
    record['actual_model_requests']=record.get('model_trace',{}).get('dispatched',0)
    record['independently_verified']=any(a.get('verification',{}).get('independently_verified_owned_development') for a in record['attempts'])
    record.update(cycle_wall_seconds=round(time.monotonic()-began,3),additional_spending_usd=0,
        commercial_admission='NOT_ADMITTED',private_execution_admitted=False)
    record['receipt_sha256']=receipt_hash(record)
    return record


def run(expected,wheels,selection='QWEN_COMPARISON'):
    from bountyforge.phase8_evaluation import require_credential_free_host
    require_credential_free_host();install_stop_handler();plan=load_plan(expected,selection)
    profile='QWEN_1_5B' if selection=='QWEN_COMPARISON' else 'GRANITE42_3B'
    capacity((3 if profile=='QWEN_1_5B' else 5)*1024**3)
    if CLAIMS.is_symlink():raise ValueError('PRIVATE_STORE_REQUIRED')
    CLAIMS.mkdir(mode=0o700,exist_ok=True)
    if CLAIMS.stat().st_uid!=os.getuid() or CLAIMS.stat().st_mode&0o077:raise ValueError('PRIVATE_STORE_REQUIRED')
    descriptor=os.open(CLAIMS/'worker.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        RESULTS.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='bf21-owned-') as temp:
            root=Path(temp);root.chmod(0o755)
            assets_proof=stage_assets(root/'assets',Path.home()/'.cache/bountyforge',profile=profile)
            # Release only this run's cold staged model pages after copying.
            # This is normal file-cache advice, not a global cache/cgroup change.
            with (root/'assets/model.gguf').open('rb') as staged:
                os.posix_fadvise(staged.fileno(),0,0,os.POSIX_FADV_DONTNEED)
            extract_offline_runtime(wheels,root/'native');stage_native_cache(root/'native')
            docker=shutil.which('docker')
            if not docker:raise ValueError('DOCKER_REQUIRED')
            rows=[]
            for case in CASES:
                for selected in plan['arms']:
                    work=root/(case+'--'+selected);work.mkdir();work.chmod(0o755)
                    record=run_arm(case,selected,root/'assets',root/'native',work,docker,expected)
                    record['assets']=assets_proof;record['receipt_sha256']=receipt_hash(record)
                    path=RESULTS/(case+'--'+selected+'.json')
                    with path.open('x') as out:out.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
                    rows.append({'case_id':case,'arm':selected,'status':record['status'],
                        'requests':record['actual_model_requests'],'verified':record['independently_verified']})
                    print(json.dumps(rows[-1]),flush=True)
                    with (root/'assets/model.gguf').open('rb') as staged:
                        os.posix_fadvise(staged.fileno(),0,0,os.POSIX_FADV_DONTNEED)
            return rows


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--admit-owned-evaluation',action='store_true');p.add_argument('--experiment-sha256',required=True)
    p.add_argument('--wheel-directory',type=Path,required=True)
    p.add_argument('--selection',choices=('QWEN_COMPARISON','GRANITE_TRIAL'),default='QWEN_COMPARISON')
    args=p.parse_args(argv)
    if not args.admit_owned_evaluation:p.error('Explicit frozen owned evaluation admission required')
    rows=run(args.experiment_sha256,args.wheel_directory,args.selection)
    return 0 if all(r['status']=='COMPLETED' for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
