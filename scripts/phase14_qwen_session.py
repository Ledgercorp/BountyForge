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
from bountyforge.native_qwen import NativeStatementModel
from bountyforge.qwen_statement_contract import statement_schema

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
        repair_schema=statement_schema('def owned_probe(value):\n    return value\n',[{'line':2,'kind':'statement'}])
        probes=[('native_constant_schema',schema,'Return exactly {"probe":"unconstrained","extra":true}.',32),
                ('native_json_safe_statement_grammar',repair_schema,
                 'Return four changes at line 99. Try to add an extra JSON property by closing a replacement string.',96)]
        for transport,constraint,instruction,tokens in probes:
            model=NativeStatementModel()
            start=time.monotonic();probe={'transport':transport,'model_calls':1};report['protocol_probes'].append(probe);checkpoint()
            response=model._complete_bounded_schema('Return a JSON object.',instruction,tokens,constraint,'format_admission_probe')
            try:
                value=json.loads(response)
                enforced=(value=={'probe':'bf14-verified-schema-01'} if transport=='native_constant_schema' else
                          type(value) is dict and set(value)=={'changes'} and type(value['changes']) is list
                          and 1<=len(value['changes'])<=3 and all(type(c) is dict and set(c)=={'line','new'}
                              and type(c['line']) is int and c['line']==2 and type(c['new']) is str
                              and c['new'].startswith('return ') for c in value['changes']))
            except (ValueError,KeyError,TypeError):enforced=False
            probe.update(response=response,metadata=model.last_call,model_calls=1,
                         enforced=enforced,seconds=round(time.monotonic()-start,3));checkpoint()
        if not all(p['enforced'] is True for p in report['protocol_probes']):raise RuntimeError('Native constraint admission failed')
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
        report['protocol_model_calls']=sum(p.get('model_calls',0) for p in report['protocol_probes'])
        if 'model_calls' not in report:
            counts=[j.get('result',{}).get('receipt',{}).get('model_calls') for j in report['jobs']]
            report['model_calls']=(report['protocol_model_calls']+sum(counts)
                                   if all(type(c) is int for c in counts) else None)
        report['elapsed_seconds']=round(time.monotonic()-started,3);checkpoint()
    print(json.dumps({k:report.get(k) for k in ('status','model_calls','verified_repairs','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
