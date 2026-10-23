"""Manual-only sequential owned comparison. No provider fallback or shell tools."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
from bountyforge.inference_envelopes import envelope_spec
from bountyforge.local_model_runtime import LocalRuntime
from bountyforge.model_profiles import profile_spec
from bountyforge.nextgen_repair import TrialStatementModel,mapped_prompt
from bountyforge.owned_repair_queue import OwnedRepairQueue
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import ROOT,RepairService,catalog,digest,receipt_hash,strict_json

PROFILES=('QWEN_1_5B','QWEN35_4B','GRANITE42_3B')
CASES=('cursor-checkpoint','interval-compaction','retry-decision')
CONFIG=ROOT/'experiments/nextgen/comparison.json'
CODE=tuple(sorted([p.relative_to(ROOT).as_posix() for p in (ROOT/'bountyforge').glob('*.py')]
    +['scripts/nextgen_comparison.py']))


def verify_experiment(expected):
    if not re.fullmatch('[a-f0-9]{64}',expected) or CONFIG.is_symlink() or CONFIG.stat().st_size>50000:
        raise ValueError('FROZEN_EXPERIMENT_REJECTED')
    raw=CONFIG.read_bytes()
    if digest(raw)!=expected:raise ValueError('FROZEN_EXPERIMENT_CHANGED')
    value=strict_json(raw)
    if (value['model_profiles']!=list(PROFILES) or value['case_ids']!=list(CASES)
            or value['envelope']!=envelope_spec('NEXTGEN_TRIAL')
            or value['budgets']!={'tasks_per_model':3,'attempts_per_task':2,'maximum_completion_requests':18,
                                 'input_token_limit':1200,'cpu_threads':4}
            or set(value['code_sha256'])!=set(CODE)):
        raise ValueError('BOUNDED_EXPERIMENT_REQUIRED')
    for name,sha in value['code_sha256'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('EXPERIMENT_IMPLEMENTATION_CHANGED')
    specs={c['id']:c for c in catalog()}
    if value['cases']!=[specs[c] for c in CASES] or value['models']!=[profile_spec(p) for p in PROFILES]:
        raise ValueError('EXPERIMENT_ASSETS_CHANGED')
    return value


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment-sha256',required=True);p.add_argument('--output',required=True)
    args=p.parse_args(argv);output=Path(args.output);began=time.monotonic()
    report={'kind':'nextgen_local_model_comparison','status':'BLOCKED','stage':'FREE_HOST_GATE',
        'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,'independent_accuracy':None,
        'additional_spending_usd':0,'inference_spending_usd':0,'default_replaced':False,'paid_fallback':False,
        'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
        'experiment_sha256':args.experiment_sha256,'models':[]}
    def checkpoint():
        raw=json.dumps(report,indent=2,sort_keys=True)+'\n'
        if len(raw.encode())>500000:raise ValueError('EVIDENCE_BUDGET_EXCEEDED')
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(raw)
        model=report['models'][-1] if report['models'] else {}
        print(json.dumps({'stage':report['stage'],'profile':model.get('model_profile'),
            'jobs_observed':len(model.get('jobs',[])),'elapsed_seconds':round(time.monotonic()-began,1)}),flush=True)
    try:
        required={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
            'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021','RUNNER_OS':'Linux','RUNNER_ARCH':'X64',
            'BOUNTYFORGE_NEXTGEN_FREE_ACK':'true'}
        if any(os.environ.get(k)!=v for k,v in required.items()):raise ValueError('FREE_STANDARD_PUBLIC_RUNNER_REQUIRED')
        require_credential_free_host();config=verify_experiment(args.experiment_sha256);report['frozen_experiment']=config
        available=int(next(r.split()[1] for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:')))
        report['host']={'logical_cpus':os.cpu_count(),'available_memory_kib':available,'disk_free_bytes':shutil.disk_usage(ROOT).free}
        if (os.cpu_count() or 0)<4 or available<12*1024**2 or report['host']['disk_free_bytes']<2*1024**3:
            raise RuntimeError('RESOURCE_CAPACITY_UNAVAILABLE')
        queue=OwnedRepairQueue(service_factory=lambda:RepairService(model_factory=TrialStatementModel,
                prompt_factory=mapped_prompt,resource_envelope='NEXTGEN_TRIAL'))
        for profile in PROFILES:
            started=time.monotonic();row={'model_profile':profile,'jobs':[],'status':'BLOCKED'};report['models'].append(row)
            batch='nextgen-'+profile.lower();queue.create(batch,'QWEN_LOCAL',list(CASES),model_profile=profile)
            report['stage']='AUTONOMOUS_QUEUE';checkpoint()
            for case in CASES:
                entry={'case_id':case};row['jobs'].append(entry);t=time.monotonic()
                entry['preparation']=queue.claim(batch);checkpoint();job=entry['preparation']
                if job.get('task',{}).get('case_id')!=case or job['task']['model_profile']!=profile:
                    row['blocking_reason']='PREPARATION_IDENTITY_FAILURE';queue.stop(batch);break
                done=threading.Event();heartbeat={'renewals':0,'failed':False};entry['heartbeat']=heartbeat
                def renew():
                    while not done.wait(30):
                        try:queue.heartbeat(batch,job['job_id'],job['lease_token']);heartbeat['renewals']+=1
                        except (ValueError,OSError,RuntimeError):heartbeat['failed']=True;return
                thread=threading.Thread(target=renew,daemon=True)
                try:
                    with LocalRuntime(profile,threads=4,resource_envelope='NEXTGEN_TRIAL') as runtime:
                        # Launch the resource-limited process before adding a
                        # heartbeat thread: preexec_fn must not run after fork
                        # from this controller with an active Python thread.
                        thread.start()
                        entry['runtime']=runtime.measurement;checkpoint()
                        entry['result']=queue.run_qwen(batch,job['job_id'],job['lease_token'])
                except (ValueError,OSError,RuntimeError) as exc:
                    entry['runtime_error']=str(exc) if re.fullmatch('[A-Z_]{1,80}',str(exc)) else type(exc).__name__
                    row['blocking_reason']='RUNTIME_OR_RESOURCE_FAILURE'
                finally:
                    done.set()
                    if thread.ident is not None:thread.join(timeout=2)
                    entry['elapsed_seconds']=round(time.monotonic()-t,3);checkpoint()
                if (row.get('blocking_reason') or heartbeat['failed'] or entry.get('runtime',{}).get('unexpected_exit')
                        or entry.get('runtime',{}).get('wall_limit_reached') or entry.get('result',{}).get('state')=='BLOCKED'):
                    row.setdefault('blocking_reason','WORKER_BLOCKED');queue.stop(batch);break
            row['queue_status']=queue.status(batch)
            row['status']='COMPLETED' if len(row['jobs'])==3 and not row.get('blocking_reason') else 'BLOCKED'
            row['elapsed_seconds']=round(time.monotonic()-started,3);checkpoint()
        report['stage']='COMPARISON_FINISHED'
        report['status']='COMPLETED' if all(m['status']=='COMPLETED' for m in report['models']) else 'PARTIAL_BLOCKED'
    except (RuntimeError,ValueError,OSError,KeyError,TypeError) as exc:
        report['blocking_reason']=str(exc) if re.fullmatch('[A-Z_]{1,80}',str(exc)) else type(exc).__name__
    finally:
        report['elapsed_seconds']=round(time.monotonic()-began,3);report['receipt_sha256']=receipt_hash(report);checkpoint()
    print(json.dumps({k:report[k] for k in ('status','stage','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
