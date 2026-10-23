"""Actual contained SDK handshake and capability probes. Never starts a turn."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from phase17_isolation import IMAGE,IsolationUnavailable,docker_command,validate_observation,host_gate
from phase17_sdk_bootstrap import (extract_offline_runtime,sdk_bootstrap_command,RUNTIME_BIN,
    _rpc_response,sanitized_boot_diagnostic)
from phase19_native_binding import stage_native_cache

ROOT=Path(__file__).resolve().parent
FORBIDDEN=('bash','pwsh','exec_command','write_stdin','write','edit','read','read_image',
           'list_mcp_resources','list_mcp_resource_templates','read_mcp_resource','run_code')
LOAD_PROBE=r'''
import ctypes,json,pathlib
source=pathlib.Path('/opt/harness/native-cache/node-addon-require-builtin-linux-x64-gnu/0.1.9/linux-x64-gnu/linux-x64-gnu-napi-v9.node')
target=pathlib.Path('/tmp/binding.node');target.write_bytes(source.read_bytes())
try:
    ctypes.CDLL(str(target))
    denied=False
except OSError as error:
    denied='failed to map segment' in str(error)
finally:target.unlink()
print(json.dumps({'same_binding_tmp_noexec_mapping_denied':denied}))
'''


def validate_audit(record):
    if (type(record) is not dict or record.get('kind')!='BOUNTYFORGE_LIVE_SDK_CAPABILITY_AUDIT'
            or record.get('model_requests')!=0 or record.get('mcp_resources_service_present') is not False
            or type(record.get('tool_names')) is not list or set(record['tool_names']) & set(FORBIDDEN)):
        raise IsolationUnavailable('SDK_LIVE_CAPABILITY_AUDIT_REJECTED')
    rows=record.get('refusals')
    if (type(rows) is not list or [x.get('tool') for x in rows]!=list(FORBIDDEN)
            or any(x.get('available') is not False or x.get('invoked') is not True or x.get('unknown_tool') is not True for x in rows)):
        raise IsolationUnavailable('SDK_LIVE_TOOL_REFUSAL_UNCONFIRMED')
    return record


def _run_fixed(command,timeout=35):
    name=next((v.removeprefix('--name=') for v in command if v.startswith('--name=')),None)
    if name is None or not re.fullmatch('bf-p17-[0-9a-f]{16}',name):raise IsolationUnavailable('OWNED_CONTAINER_ID_REQUIRED')
    try:
        result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,timeout=timeout,
            env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'})
        if result.returncode!=0 or len(result.stdout)>16384:raise IsolationUnavailable('CONTAINED_CONTROL_PROBE_FAILED')
        return result.stdout.decode()
    finally:remove_container(command[0],name)


def remove_container(docker,name):
    env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'}
    subprocess.run([docker,'rm','-f',name],capture_output=True,timeout=8,env=env)
    check=subprocess.run([docker,'ps','-aq','--filter','name=^/'+name+'$'],capture_output=True,timeout=8,env=env)
    if check.returncode!=0 or check.stdout.strip():raise IsolationUnavailable('SDK_CLEANUP_UNCONFIRMED')


def lifecycle_probes(docker,workspace,native):
    """Kill an initialized real runtime, prove cleanup, then start a fresh one."""
    results=[]
    for interrupted in (True,False):
        name='bf-p17-'+uuid.uuid4().hex[:16]
        cmd=sdk_bootstrap_command(docker,workspace,name,native)
        cmd[-5:]=[IMAGE,'/opt/harness/'+RUNTIME_BIN,'--profile','sdk-minimal','--patch','/workspace/audit.patch.yml']
        cmd.insert(cmd.index(IMAGE),'-i')
        child=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            bufsize=0,env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'},start_new_session=True)
        try:
            def request(identity,method,params=None):
                child.stdin.write((json.dumps({'jsonrpc':'2.0','id':identity,'method':method,'params':params})+'\n').encode())
                child.stdin.flush();return _rpc_response(child,identity,timeout=20)
            result=request('lifecycle-init','initialize',{'cwd':'/workspace','provider':'deepseek-official','model':'deepseek-v4-flash'})
            if result.get('serverInfo',{}).get('name')!='deepseek-harness-sdk-runtime':
                raise IsolationUnavailable('SDK_RESTART_IDENTITY_UNCONFIRMED')
            if interrupted:
                killed=subprocess.run([docker,'kill',name],capture_output=True,timeout=8,
                    env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'})
                if killed.returncode!=0:raise IsolationUnavailable('SDK_INTERRUPTION_UNCONFIRMED')
            else:request('lifecycle-shutdown','shutdown')
            child.stdin.close();child.wait(timeout=8)
            if (interrupted and child.returncode==0) or (not interrupted and child.returncode!=0):
                raise IsolationUnavailable('SDK_LIFECYCLE_EXIT_REJECTED')
            results.append({'mode':'forced-termination' if interrupted else 'fresh-process-restart',
                'initialize_confirmed':True,'exit_code':child.returncode,'model_requests':0})
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
            remove_container(docker,name)
        results[-1]['container_absent_after_cleanup']=True
    return results


def run(wheels,execution_host):
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        raise IsolationUnavailable('LINUX_X64_ONLY')
    if execution_host=='github-actions':host_gate()
    elif execution_host!='codex-session':raise IsolationUnavailable('EXPLICIT_EXECUTION_HOST_REQUIRED')
    docker=shutil.which('docker')
    if not docker or not Path(docker).is_absolute():raise IsolationUnavailable('DOCKER_UNAVAILABLE')
    record={'kind':'PHASE19_MODEL_FREE_SDK_ACCEPTANCE','execution_host':execution_host,
        'status':'BLOCKED','model_requests':0,'agent_turns':0,'commercial_admission':'NOT_ADMITTED',
        'private_execution_admitted':False,'additional_spending_usd':0}
    began=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='bf-p19-') as temp:
        root=Path(temp);root.chmod(0o755);workspace=root/'workspace';workspace.mkdir(mode=0o755);workspace.chmod(0o755)
        canary=workspace/'owned.txt';canary.write_text('owned-development-only\n');canary.chmod(0o644)
        name='bf-p17-'+uuid.uuid4().hex[:16]
        record['boundary']=validate_observation(_run_fixed(docker_command(docker,workspace,name)).strip())
        native=root/'native';record['archives']=extract_offline_runtime(wheels,native)
        record['native_cache']=stage_native_cache(native)
        name='bf-p17-'+uuid.uuid4().hex[:16]
        load=sdk_bootstrap_command(docker,workspace,name,native)
        load[-5:]=[IMAGE,'python','-I','-B','-c',LOAD_PROBE]
        record['load_probe']=json.loads(_run_fixed(load))
        if record['load_probe'].get('same_binding_tmp_noexec_mapping_denied') is not True:
            raise IsolationUnavailable('NATIVE_NOEXEC_CAUSE_NOT_CONFIRMED')
        patch=workspace/'audit.patch.yml'
        audit=(ROOT/'phase19/runtime_audit.mjs').read_bytes();(workspace/'runtime_audit.mjs').write_bytes(audit)
        (workspace/'runtime_audit.mjs').chmod(0o444)
        patch.write_bytes((ROOT/'phase17/hardened-sdk-minimal.patch.yml').read_bytes()+b'\n- insert:\n    - id: bountyforge-runtime-audit\n      name: /workspace/runtime_audit.mjs\n')
        patch.chmod(0o444);record['owned_audit_sha256']=hashlib.sha256(audit).hexdigest()
        name='bf-p17-'+uuid.uuid4().hex[:16];cmd=sdk_bootstrap_command(docker,workspace,name,native)
        cmd[-5:]=[IMAGE,'/opt/harness/'+RUNTIME_BIN,'--profile','sdk-minimal','--patch','/workspace/audit.patch.yml']
        cmd.insert(cmd.index(IMAGE),'-i')
        error_file=root/'sdk.stderr'
        with error_file.open('wb') as errors:
            child=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'},start_new_session=True)
            def request(identity,method,params=None):
                child.stdin.write((json.dumps({'jsonrpc':'2.0','id':identity,'method':method,'params':params})+'\n').encode());child.stdin.flush()
                return _rpc_response(child,identity,timeout=20)
            try:
                result=request('p19-init','initialize',{'cwd':'/workspace','provider':'deepseek-official','model':'deepseek-v4-flash'})
                if result.get('serverInfo',{}).get('name')!='deepseek-harness-sdk-runtime':
                    raise IsolationUnavailable('AUTHENTIC_SDK_IDENTITY_UNCONFIRMED')
                record['initialize_result']=result
                record['owned_idle_session']=request('p19-idle','session/working-directory/get',{'sessionId':'bountyforge-model-free-audit'})
                measurement="import json,pathlib; p=pathlib.Path('/sys/fs/cgroup'); print(json.dumps({n:(p/n).read_text().strip() if (p/n).exists() else None for n in ('memory.peak','memory.max','pids.peak','pids.max','cpu.max','cpu.stat')}))"
                stats=subprocess.run([docker,'exec',name,'python','-I','-B','-c',measurement],capture_output=True,
                    timeout=8,env={'HOME':'/tmp','PATH':'/usr/local/bin:/usr/bin:/bin'})
                if stats.returncode!=0 or len(stats.stdout)>4096:raise IsolationUnavailable('SDK_RESOURCE_OBSERVATION_FAILED')
                record['actual_container_resources']=json.loads(stats.stdout)
                record['resource_measurement_scope']='Whole SDK cgroup including the owned measurement process'
                # The hook awaits every registry refusal before this response.
                request('p19-shutdown','shutdown');child.stdin.close();child.wait(timeout=8)
                if child.returncode!=0:raise IsolationUnavailable('SDK_EXIT_NOT_CLEAN')
                record.update(initialize_confirmed=True,shutdown_confirmed=True,exit_code=child.returncode)
            except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
                record['failure_code']=str(exc) if isinstance(exc,IsolationUnavailable) else type(exc).__name__
            finally:
                if child.poll() is None:child.kill();child.wait(timeout=5)
                remove_container(docker,name);record['container_absent_after_cleanup']=True
        raw=error_file.read_bytes()
        if len(raw)>65536:raise IsolationUnavailable('SDK_DIAGNOSTIC_BUDGET_EXCEEDED')
        audits=[json.loads(line.partition(b'BOUNTYFORGE_AUDIT ')[2]) for line in raw.splitlines() if line.startswith(b'BOUNTYFORGE_AUDIT ')]
        if len(audits)==1:record['runtime_audit']=validate_audit(audits[0])
        else:record['audit_missing']=True
        record['diagnostic']=sanitized_boot_diagnostic(raw)
        record['canary_unchanged']=canary.read_text()=='owned-development-only\n'
        record['lifecycle_probes']=lifecycle_probes(docker,workspace,native)
        record['status']='PASSED' if all(record.get(k) is True for k in ('initialize_confirmed','shutdown_confirmed','container_absent_after_cleanup','canary_unchanged')) and 'runtime_audit' in record else 'BLOCKED'
    record['elapsed_seconds']=round(time.monotonic()-began,3)
    from bountyforge.repair_engines import receipt_hash
    record['receipt_sha256']=receipt_hash(record)
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wheel-directory',type=Path,required=True)
    p.add_argument('--execution-host',choices=('github-actions','codex-session'),required=True)
    p.add_argument('--admit-model-free-probe',action='store_true');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if not args.admit_model_free_probe:p.error('Explicit model-free probe acknowledgement required')
    result=run(args.wheel_directory,args.execution_host)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result.get(k) for k in ('status','failure_code','initialize_confirmed','shutdown_confirmed','model_requests')}))
    return 0 if result['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
