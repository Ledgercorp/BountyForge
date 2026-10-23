"""Frozen developmental comparison, standard public CPU only; no paid fallback."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import time

from bountyforge.curated_tasks import editable_scope
from bountyforge.local_model_runtime import LocalRuntime
from bountyforge.model_profiles import PROFILES
from bountyforge.owned_repair_queue import OwnedRepairQueue
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.profiled_qwen import ProfiledStatementModel
from bountyforge.repair_engines import ROOT,RepairService,catalog,digest,receipt_hash,strict_json,qwen_availability
from bountyforge.repair_intelligence import compact_model_prompt as model_prompt,source_context
from bountyforge.statements import statement_catalog,SYSTEM

CONFIGS={'v1':ROOT/'experiments/phase15/comparison.json','v2':ROOT/'experiments/phase15/comparison-v2.json',
         'v3':ROOT/'experiments/phase15/comparison-v3.json','v4':ROOT/'experiments/phase15/comparison-v4.json'}
CASES=('reserve-release','response-normalize','weighted-window')
CODE_PATHS=('bountyforge/repair_engines.py','bountyforge/model_profiles.py','bountyforge/profiled_qwen.py',
    'bountyforge/local_model_runtime.py','bountyforge/native_qwen.py','bountyforge/qwen_statement_contract.py',
    'bountyforge/repair_intelligence.py','bountyforge/statement_grammar.py','bountyforge/owned_repair_queue.py',
    'bountyforge/phase8_evaluation.py','bountyforge/curated_docker.py','bountyforge/curated_tasks.py',
    'bountyforge/repair_session.py','bountyforge/drafts.py','bountyforge/statements.py','bountyforge/model.py',
    'bountyforge/mcp_server.py','scripts/repair_engine.py','scripts/owned_queue.py','scripts/local_inference.py',
    'scripts/phase15_model_comparison.py')


def verify_experiment(expected,version='v1'):
    config_path=CONFIGS[version]
    if not re.fullmatch('[a-f0-9]{64}',expected) or config_path.is_symlink() or config_path.stat().st_size>30000:
        raise ValueError('FROZEN_EXPERIMENT_REJECTED')
    raw=config_path.read_bytes()
    if digest(raw)!=expected:raise ValueError('FROZEN_EXPERIMENT_CHANGED')
    config=strict_json(raw)
    budgets={
        'tasks_per_model':3,'attempts_per_task':2,'completion_tokens':150,'request_timeout_seconds':45,
        'context_tokens':2048,'resource_probe_calls_per_model':1,'maximum_completion_requests':14}
    if version in ('v3','v4'):budgets.update(tasks_per_model=1,resource_probe_calls_per_model=0,maximum_completion_requests=4,input_token_limit=700)
    if version=='v4':budgets['cpu_threads']=4
    if config['model_profiles']!=list(PROFILES) or config['budgets']!=budgets:
        raise ValueError('EXPERIMENT_BUDGET_CHANGED')
    if config['case_ids']!=(['weighted-window'] if version in ('v3','v4') else list(CASES)) or set(config['code_sha256'])!=set(CODE_PATHS):raise ValueError('BOUNDED_CASES_REQUIRED')
    for name,sha in config['code_sha256'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('EXPERIMENT_IMPLEMENTATION_CHANGED')
    specs={s['id']:s for s in catalog()}
    if [specs[c] for c in config['case_ids']]!=config['cases']:raise ValueError('EXPERIMENT_TASKS_CHANGED')
    return config


def resource_prompt():
    # Separate owned calibration: never scored, executed, or reused as a benchmark task.
    source=('def fold_entries(entries, initial):\n    total = initial\n    for value in entries:\n'
            '        if value is None:\n            continue\n        total = value\n    return total\n')
    scope=editable_scope(source,'fold_entries');units=statement_catalog(source,scope)
    public={'approved_file':'subject.py','source':source,'target_symbol':'fold_entries',
        'description':'Owned resource calibration only; aggregate entries without modifying caller data. ',
        'editable_lines':sorted(units),'edit_units':[{k:v[k] for k in ('line','end_line','kind','bindings')} for v in units.values()],
        'proposal_protocol':'ast_statement_v1','source_context':source_context(source,'fold_entries',sorted(units)),
        'baseline_feedback':{'failing_tests':[],'assertions':[],'classification':'RESOURCE_PROBE_NO_TESTS_EXECUTED'}}
    while len(model_prompt(public,None).encode())<3300:
        public['description']+='The caller retains ownership of entries; keep processing bounded and free of I/O. '
    return model_prompt(public,None)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment-sha256',required=True);p.add_argument('--output',required=True)
    p.add_argument('--experiment',choices=CONFIGS,default='v1')
    args=p.parse_args(argv);path=Path(args.output);started=time.monotonic()
    report={'kind':'phase15_local_model_comparison','status':'BLOCKED','stage':'FREE_HOST_GATE',
        'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,'independent_accuracy':None,
        'additional_spending_usd':0,'inference_spending_usd':0,'default_replaced':False,'paid_fallback':False,
        'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
        'experiment_sha256':args.experiment_sha256,'models':[]}
    def checkpoint():
        raw=json.dumps(report,indent=2,sort_keys=True)+'\n'
        if len(raw.encode())>500000:raise ValueError('EVIDENCE_BUDGET_EXCEEDED')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw)
    try:
        required={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
            'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021','RUNNER_OS':'Linux','RUNNER_ARCH':'X64',
            'BOUNTYFORGE_PHASE15_FREE_ACK':'true'}
        if any(os.environ.get(k)!=v for k,v in required.items()):raise ValueError('FREE_STANDARD_PUBLIC_RUNNER_REQUIRED')
        require_credential_free_host();config=verify_experiment(args.experiment_sha256,args.experiment);report['frozen_experiment']=config
        mem={r.split(':')[0]:int(r.split()[1]) for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith(('MemTotal:','MemAvailable:'))}
        report['host']={'logical_cpus':os.cpu_count(),'memory_kib':mem,'disk_free_bytes':shutil.disk_usage(ROOT).free}
        threads=config['budgets'].get('cpu_threads',2)
        if (os.cpu_count() or 0)<threads or mem['MemAvailable']<12*1024**2 or report['host']['disk_free_bytes']<2*1024**3:
            raise RuntimeError('RESOURCE_CAPACITY_UNAVAILABLE')
        queue=OwnedRepairQueue(service_factory=(lambda:RepairService(model_factory=lambda **kw:ProfiledStatementModel(prompt_token_limit=700,**kw)))
                               if args.experiment in ('v3','v4') else RepairService)
        prompt=resource_prompt()
        for profile in config['model_profiles']:
            begin=time.monotonic();engine={'model_profile':profile,'status':'BLOCKED','jobs':[]};report['models'].append(engine)
            report['stage']='RESOURCE_ADMISSION';probe={'prompt':strict_json(prompt),'prompt_sha256':digest(prompt.encode())}
            engine['resource_probe']=probe;checkpoint()
            try:
                if args.experiment in ('v3','v4'):
                    # Reuse completed pinned resource receipts; narrow both inputs
                    # below failed probes. Every actual request is token-checked.
                    engine['resource_probe']={'completion_requests':0,'metadata':{'completion_requests':0},
                        'mode':'PRIOR_PINNED_RESOURCE_RECEIPTS_WITH_LIVE_700_TOKEN_GATE',
                        'prior_resource_runs':[40001954401,40007714754,40009784193]}
                    engine['resource_admitted']=True
                else:
                    with LocalRuntime(profile,threads=threads) as runtime:
                        probe['runtime']=runtime.measurement
                        if not qwen_availability(profile):raise RuntimeError('SELECTED_PROCESS_NOT_ADMITTED')
                        other=next(p for p in PROFILES if p!=profile)
                        probe['unselected_profile_available']=qwen_availability(other)
                        if probe['unselected_profile_available']:raise RuntimeError('LOCAL_MODEL_IDENTITY_AMBIGUOUS')
                        model=ProfiledStatementModel(timeout_seconds=45);t=time.monotonic()
                        try:
                            probe['response']=model.complete_line(SYSTEM,prompt,max_tokens=150)
                            probe['response_sha256']=digest(probe['response'].encode())
                        finally:
                            probe['inference_seconds']=round(time.monotonic()-t,3);probe['metadata']=model.last_call
                    if (not runtime.measurement['server_stopped'] or runtime.measurement['wall_limit_reached']
                            or runtime.measurement.get('unexpected_exit')):raise RuntimeError('RUNTIME_BOUNDARY_OR_EXIT_FAILURE')
                    engine['resource_admitted']=True
            except (RuntimeError,ValueError,OSError) as exc:
                engine.update(blocking_reason=str(exc) if re.fullmatch('[A-Z_]{1,80}',str(exc)) else type(exc).__name__,resource_admitted=False)
                engine['elapsed_seconds']=round(time.monotonic()-begin,3);checkpoint();continue
            batch='phase15-'+profile.lower();queue.create(batch,'QWEN_LOCAL',config['case_ids'],model_profile=profile)
            report['stage']='AUTONOMOUS_QUEUE';checkpoint()
            for expected in config['case_ids']:
                entry={'case_id':expected};engine['jobs'].append(entry);job_started=time.monotonic()
                entry['preparation']=queue.claim(batch);checkpoint();task=entry['preparation'].get('task')
                if task is None:engine['blocking_reason']='OWNED_PREPARATION_BLOCKED';break
                if task['case_id']!=expected or task['model_profile']!=profile:raise ValueError('QUEUE_IDENTITY_MISMATCH')
                try:
                    with LocalRuntime(profile,threads=threads) as runtime:
                        entry['runtime']=runtime.measurement
                        entry['unselected_profile_available']=qwen_availability(next(p for p in PROFILES if p!=profile))
                        if entry['unselected_profile_available']:raise RuntimeError('LOCAL_MODEL_IDENTITY_AMBIGUOUS')
                        entry['result']=queue.run_qwen(batch,entry['preparation']['job_id'],entry['preparation']['lease_token'])
                except (RuntimeError,ValueError,OSError) as exc:
                    entry['runtime_error']=str(exc) if re.fullmatch('[A-Z_]{1,80}',str(exc)) else type(exc).__name__
                    queue.stop(batch);engine['blocking_reason']='RUNTIME_OR_RESOURCE_FAILURE';break
                finally:entry['elapsed_seconds']=round(time.monotonic()-job_started,3);checkpoint()
                if (entry['result']['state']=='BLOCKED' or not runtime.measurement['server_stopped']
                        or runtime.measurement['wall_limit_reached'] or runtime.measurement.get('unexpected_exit')):
                    queue.stop(batch);engine['blocking_reason']='WORKER_BLOCKED';break
            engine['queue_status']=queue.status(batch)
            engine['status']='COMPLETED' if len(engine['jobs'])==len(config['case_ids']) and not engine.get('blocking_reason') else 'BLOCKED'
            engine['elapsed_seconds']=round(time.monotonic()-begin,3);checkpoint()
        report['stage']='COMPARISON_FINISHED';report['status']='COMPLETED' if all(m['status']=='COMPLETED' for m in report['models']) else 'PARTIAL_BLOCKED'
    except (RuntimeError,ValueError,OSError,KeyError,TypeError) as exc:report['blocking_reason']=type(exc).__name__
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3);report['receipt_sha256']=receipt_hash(report);checkpoint()
    print(json.dumps({k:report[k] for k in ('status','stage','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
