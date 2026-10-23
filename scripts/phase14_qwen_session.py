"""Independent bounded local Qwen owned-queue session on standard public Linux."""
import argparse
import json
import os
from pathlib import Path
import time
from bountyforge.owned_repair_queue import OwnedRepairQueue
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import receipt_hash
from bountyforge.repair_engines import qwen_availability
from bountyforge.model import LocalModel
from bountyforge.native_qwen import NativeStatementModel

CASES=['invoice-summary','cursor-adapter','retry-policy']


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);started=time.monotonic();path=Path(args.output)
    report={'kind':'phase14_autonomous_qwen_queue','engine':'QWEN_LOCAL',
            'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
            'status':'BLOCKED','jobs':[],'max_model_calls':8,'max_repair_model_calls':6,
            'protocol_probes':[],'additional_spending_usd':0,
            'model_api_cost_usd':0,'paid_fallback':False,
            'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID')}
    def checkpoint():
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(report,indent=2,sort_keys=True)+'\n'
        if len(raw.encode())>400000:raise ValueError('Evidence output exceeded bound')
        path.write_text(raw)
    try:
        required={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
                  'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021',
                  'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','BOUNTYFORGE_PHASE14_QWEN_ACK':'true'}
        if any(os.environ.get(k)!=v for k,v in required.items()):raise ValueError('Explicit free hosted gate required')
        require_credential_free_host()
        if not qwen_availability():raise RuntimeError('Pinned local runtime unavailable')
        report['host']={'logical_cpus':os.cpu_count(),'memory_kib':{
            row.split(':')[0]:int(row.split()[1]) for row in Path('/proc/meminfo').read_text().splitlines()
            if row.startswith(('MemTotal:','MemAvailable:'))}}
        schema={'type':'object','properties':{'probe':{'type':'string','const':'bf14-verified-schema-01'}},
                'required':['probe'],'additionalProperties':False}
        for transport,model in [('openai_chat_schema',LocalModel()),('native_completion_schema',NativeStatementModel())]:
            start=time.monotonic();probe={'transport':transport};report['protocol_probes'].append(probe);checkpoint()
            response=model._complete_bounded_schema('Return a JSON object.',
                'Return exactly {"probe":"unconstrained","extra":true}.',32,schema,'format_admission_probe')
            try:enforced=json.loads(response)=={'probe':'bf14-verified-schema-01'}
            except ValueError:enforced=False
            probe.update(response=response,metadata=model.last_call,model_calls=1,
                         enforced=enforced,seconds=round(time.monotonic()-start,3));checkpoint()
        if report['protocol_probes'][-1]['enforced'] is not True:raise RuntimeError('Native schema admission failed')
        queue=OwnedRepairQueue();queue.create('phase14-autonomous','QWEN_LOCAL',CASES)
        checkpoint()
        for _ in range(3):
            task=queue.claim('phase14-autonomous')
            if 'lease_token' not in task:raise ValueError('Owned queue preparation unavailable')
            entry={'preparation':task};report['jobs'].append(entry);checkpoint()
            result=queue.run_qwen('phase14-autonomous',task['job_id'],task['lease_token'])
            entry['result']=result;checkpoint()
        report['queue_status']=queue.status('phase14-autonomous')
        counts=[x['result']['receipt'].get('model_calls') for x in report['jobs']]
        report['repair_model_calls']=sum(counts) if all(type(n) is int for n in counts) else None
        report['model_calls']=sum(counts)+2 if all(type(n) is int for n in counts) else None
        if report['model_calls'] is not None and report['model_calls']>8:raise ValueError('Model budget exceeded')
        report['verified_repairs']=sum(x['result']['state']=='VERIFIED' for x in report['jobs'])
        report['status']='COMPLETED'
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        report['blocking_reason']=type(exc).__name__
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3);checkpoint()
    print(json.dumps({k:report.get(k) for k in ('status','model_calls','verified_repairs','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
