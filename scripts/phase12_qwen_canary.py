"""One development-task, two-call local Qwen integration measurement on free CI."""
import argparse
import json
import os
from pathlib import Path
import time

from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.phase8_live_qwen import MODEL_SHA256, RUNTIME_SHA256
from bountyforge.repair_engines import RepairService, receipt_hash


def validate_result(result):
    if (result.get('engine')!='QWEN_LOCAL' or type(result.get('model_calls')) is not int
            or not 1<=result['model_calls']<=2 or result.get('paid_fallback') is not False
            or len(result.get('calls',[]))!=result['model_calls']):
        raise ValueError('Local engine usage or request-budget evidence missing')
    receipt=result.get('verification_receipt',{})
    if (receipt.get('receipt_sha256')!=receipt_hash(receipt)
            or receipt.get('outcome') not in {'VERIFIED','SOURCE_REJECTED','REPEATED_PROPOSAL',
                                            'TEST_FAILED','INDEPENDENT_VERIFICATION_FAILED'}
            or receipt.get('case_id')!='sparse-average'
            or receipt.get('engine')!='QWEN_LOCAL' or receipt.get('paid_fallback') is not False):
        raise ValueError('Completed shared verification-contract receipt required')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv);began=time.monotonic()
    report={'kind':'phase12_local_qwen_engine_canary','classification':'OWNED_DEVELOPMENT',
            'independent_evaluation':False,'case_id':'sparse-average','engine':'QWEN_LOCAL',
            'status':'BLOCKED','max_model_calls':2,'paid_fallback':False,
            'additional_spending_usd':0,'model_api_cost_usd':0,
            'run_id':os.environ.get('GITHUB_RUN_ID'),'commit':os.environ.get('GITHUB_SHA')}
    report['model']={'id':'Qwen2.5-Coder-1.5B-Instruct Q4_K_M','sha256':MODEL_SHA256,
                     'runtime':'llama.cpp b11750','runtime_archive_sha256':RUNTIME_SHA256}
    try:
        if (os.environ.get('GITHUB_ACTIONS')!='true'
                or os.environ.get('GITHUB_REPOSITORY')!='Ledgercorp/BountyForge'
                or os.environ.get('GITHUB_REF')!='refs/heads/engineering/revenue-linux-scout-20261021'
                or os.environ.get('RUNNER_OS')!='Linux' or os.environ.get('RUNNER_ARCH')!='X64'
                or os.environ.get('BOUNTYFORGE_PHASE12_QWEN_ACK')!='true'):
            raise ValueError('Explicit standard-public-Linux canary required')
        require_credential_free_host()
        service=RepairService();task=service.prepare('sparse-average','QWEN_LOCAL')
        result=service.run_qwen(task['task_id'],0);report['result']=result
        validate_result(result)
        calls=result['calls']
        metadata=[c.get('metadata') for c in calls]
        def tokens(key):
            if not all(isinstance(item,dict) and type(item.get(key)) is int for item in metadata):return None
            return sum(item[key] for item in metadata)
        report.update(status='COMPLETED',model_calls=result['model_calls'],
                      verified_repairs=int(result['independently_verified']),
                      prompt_tokens=tokens('prompt_tokens'),completion_tokens=tokens('completion_tokens'))
    except (RuntimeError,OSError,ValueError,TypeError,KeyError) as exc:
        report['blocking_reason']=type(exc).__name__
    finally:
        report['elapsed_seconds']=round(time.monotonic()-began,3)
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report.get(k) for k in ('status','model_calls','verified_repairs','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1

if __name__=='__main__':raise SystemExit(main())
