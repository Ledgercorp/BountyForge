"""One-call resource probe of a pinned public model; never a repair score."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import urllib.request

from bountyforge.native_qwen import NativeStatementModel
from bountyforge.phase8_evaluation import require_credential_free_host

MODEL_SHA='509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c'
RUNTIME_SHA='152e33221c9c9d37816a8ee9943f8d87339199197c80cb692559c9756b2027d8'
REVISION='13fb94bfda8c8cf22497dc57b78f391a9acb426a'


def file_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def limits():
    for kind,value in [(resource.RLIMIT_AS,10*1024**3),(resource.RLIMIT_CPU,180),
                       (resource.RLIMIT_CORE,0),(resource.RLIMIT_FSIZE,1024*1024)]:
        resource.setrlimit(kind,(value,value))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);started=time.monotonic();child=None
    report={'kind':'phase14_7b_cpu_resource_probe','status':'BLOCKED','model_calls':0,
            'model':'Qwen2.5-Coder-7B-Instruct-Q4_K_M','revision':REVISION,'license':'Apache-2.0',
            'model_sha256':MODEL_SHA,'runtime_archive_sha256':RUNTIME_SHA,
            'max_model_calls':1,'max_completion_tokens':96,'independent_accuracy':None,
            'repair_accuracy_measured':False,'default_model_replaced':False,
            'additional_spending_usd':0,'paid_fallback':False,'stage':'FREE_HOST_GATE',
            'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID')}
    try:
        expected={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
                  'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021',
                  'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','BOUNTYFORGE_MODEL_PROFILE_ACK':'true'}
        if any(os.environ.get(k)!=v for k,v in expected.items()):raise ValueError('Free hosted gate required')
        require_credential_free_host();temp=Path(os.environ['RUNNER_TEMP'])
        model=temp/'bf14-qwen7b.gguf';runtime=Path.home()/'.cache/bountyforge/runtime'
        archive=runtime/'llama-b11750-bin-ubuntu-x64.tar.gz'
        report['stage']='ASSET_INTEGRITY'
        if model.stat().st_size!=4683073536 or file_digest(model)!=MODEL_SHA or file_digest(archive)!=RUNTIME_SHA:
            raise ValueError('Asset digest rejected')
        # Verified trusted release only, fixed executable; no caller command.
        subprocess.run(['tar','-xzf',str(archive),'-C',str(runtime),'--no-same-owner','--no-same-permissions'],check=True,timeout=30)
        binary=runtime/'llama-b11750/llama-server'
        report['stage']='SERVER_START';load_started=time.monotonic()
        with (temp/'bf14-7b-server.log').open('wb') as log:
            child=subprocess.Popen([str(binary),'-m',str(model),'--host','127.0.0.1','--port','18080',
                '-t','2','-c','2048','-np','1'],env={'PATH':'/usr/local/bin:/usr/bin:/bin',
                'LD_LIBRARY_PATH':str(binary.parent)},stdout=log,stderr=log,preexec_fn=limits)
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                if child.poll() is not None:raise RuntimeError('Resource-bounded server exited')
                try:
                    with opener.open('http://127.0.0.1:18080/health',timeout=1) as response:
                        if json.loads(response.read(1024)).get('status')=='ok':break
                except (OSError,ValueError):pass
                time.sleep(1)
            else:raise RuntimeError('Server readiness timeout')
            report['load_seconds']=round(time.monotonic()-load_started,3)
            report['stage']='ONE_BOUNDED_INFERENCE';inference_started=time.monotonic()
            client=NativeStatementModel(endpoint='http://127.0.0.1:18080/v1/chat/completions')
            report['model_calls']=1
            report['response']=client._complete_bounded_schema('Return only a JSON object.',
                'Explain briefly why a Python collection average may require counting only non-None values.',96,
                {'type':'object','properties':{'explanation':{'type':'string','maxLength':300}},
                 'required':['explanation'],'additionalProperties':False},'cpu_feasibility')
            report['inference_seconds']=round(time.monotonic()-inference_started,3)
            report['usage']=client.last_call
            status=Path('/proc/'+str(child.pid)+'/status').read_text()
            report['server_memory_kib']={row.split(':')[0]:int(row.split()[1]) for row in status.splitlines()
                                       if row.startswith(('VmRSS:','VmHWM:','VmSize:'))}
            report['status']='COMPLETED';report['stage']='RESOURCE_PROBE_COMPLETE'
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError) as exc:
        report['error_category']=type(exc).__name__
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        report['server_stopped']=child is None or child.poll() is not None
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('status','stage','model_calls','server_stopped')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
