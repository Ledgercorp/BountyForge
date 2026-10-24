"""Paired external Qwen handoff control, same contained model and verifier."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid
from phase20_native_agent import (ROOT,ENV,claim_arm,public_file,execute,resources,model_trace)
from phase20_transport import model_command,MODEL_PROBE,validate_model_boundary,MODEL_ID
from phase19_sdk_acceptance import remove_container


def run_external_case(spec,assets,work,docker):
    from bountyforge.repair_engines import RepairService,receipt_hash
    from bountyforge.profiled_qwen import COMPACT_SYSTEM
    from bountyforge.repair_intelligence import compact_model_prompt
    from bountyforge.qwen_statement_contract import statement_schema
    from bountyforge.statement_grammar import statement_grammar
    from deepseek_owned_bridge import verify_owned_harness_response
    from deepseek_harness_handoff import HarnessHandoffRejected
    limit=claim_arm(spec['case_id'],'EXTERNAL_CONTROL')
    if limit!=1:raise ValueError('ONE_REQUEST_CONTROL_REQUIRED')
    began=time.monotonic();service=RepairService();task=service.prepare(spec['case_id'],'CODEX_AGENT')
    if any(task[k]!=spec[k] for k in ('source_sha256','tests_sha256')):raise ValueError('CONTROL_TASK_CHANGED')
    work.chmod(0o755);public_file(work/'owned.txt','owned-development-only\n')
    schema=statement_schema(task['source'],task['edit_units']);kinds={u['line']:u['kind'] for u in task['edit_units']}
    for entry in schema['properties']['changes']['items']['anyOf']:entry['x-owned-unit-kind']=kinds[entry['properties']['line']['const']]
    public_file(work/'model-config.json',json.dumps({'grammar':statement_grammar(schema,compact=True),'request_limit':1,'pi_ai_context_guard_compat':False}))
    public_file(work/'model_service.py',(ROOT/'phase20_model_service.py').read_bytes())
    public_file(work/'external_client.py',(ROOT/'phase20_external_client.py').read_bytes())
    record={'case_id':spec['case_id'],'arm':'EXTERNAL_CONTROL','candidate_author':'QWEN_LOCAL_EXTERNAL_CONTROL',
        'task':task,'status':'BLOCKED','model_requests':0,'verified_repairs':0,'native_sdk_model_requests':0,
        'independent_evaluation':False,'classification':'OWNED_DEVELOPMENT','attempts':[]}
    name='bf-p20-model-'+uuid.uuid4().hex[:16];child=None
    with (work/'process.stderr').open('wb') as errors:
        try:
            child=subprocess.Popen(model_command(docker,work,name,assets),stdin=subprocess.DEVNULL,stdout=errors,stderr=errors,env=ENV)
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if child.poll() is not None:raise RuntimeError('CONTROL_MODEL_EXITED')
                try:
                    execute(docker,name,"import urllib.request; print(urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8081/v1/models',timeout=1).read(2048).decode())",3)
                    break
                except (RuntimeError,OSError,subprocess.TimeoutExpired):time.sleep(.5)
            else:raise RuntimeError('CONTROL_MODEL_LOAD_TIMEOUT')
            record['model_boundary_before']=validate_model_boundary(json.loads(execute(docker,name,MODEL_PROBE)))
            prompt=compact_model_prompt(task,None)
            messages=[{'role':'system','content':COMPACT_SYSTEM},{'role':'user','content':prompt}]
            started=time.monotonic()
            observed=subprocess.run([docker,'exec','-i',name,'python','-I','-B','/workspace/external_client.py'],
                input=json.dumps(messages).encode(),capture_output=True,timeout=65,env=ENV)
            if observed.returncode!=0 or len(observed.stdout)>65536:raise RuntimeError('CONTROL_STREAM_REJECTED')
            output=json.loads(observed.stdout);response=output['response']
            record['model_boundary_after']=validate_model_boundary(json.loads(execute(docker,name,MODEL_PROBE)))
            trace=model_trace(docker,name)
            if trace['dispatched']!=1 or response!=trace['requests'][0]['response']:raise ValueError('CONTROL_MODEL_RESPONSE_UNBOUND')
            attempt={'model_response':response,'response_sha256':hashlib.sha256(response.encode()).hexdigest(),
                'inference_seconds':round(time.monotonic()-started,3),'usage':output['usage']}
            record['attempts'].append(attempt)
            try:attempt['verification']=verify_owned_harness_response(service,task,response,allow_owned_verification=True)
            except HarnessHandoffRejected as error:attempt['handoff_rejection']=str(error)
            record['model_resources']=resources(docker,name)
            record['status']='COMPLETED'
        except (RuntimeError,ValueError,OSError,subprocess.SubprocessError,KeyError) as error:
            record['failure']=str(error)[:150] if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__
        finally:
            try:record['model_trace']=model_trace(docker,name)
            except (RuntimeError,ValueError,OSError,subprocess.SubprocessError):pass
            if child is not None and child.poll() is None:child.kill();child.wait(timeout=5)
            remove_container(docker,name);record['containers_absent_after_cleanup']=True
    record['model_requests']=record.get('model_trace',{}).get('dispatched',0)
    record['verified_repairs']=int(any(a.get('verification',{}).get('independently_verified_owned_development') is True for a in record['attempts']))
    record.update(elapsed_seconds=round(time.monotonic()-began,3),additional_spending_usd=0,commercial_admission='NOT_ADMITTED')
    record['receipt_sha256']=receipt_hash(record)
    return record
