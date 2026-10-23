"""Four-call maximum development-only comparison of legacy and AST-bound JSON."""
import argparse
import json
import os
from pathlib import Path
import time
from bountyforge.model import LocalModel
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import RepairService, receipt_hash


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    opts=parser.parse_args(argv);began=time.monotonic()
    report={'kind':'phase13_qwen_contract_comparison','classification':'OWNED_DEVELOPMENT',
            'independent_evaluation':False,'case_id':'optional-setting','max_model_calls':4,
            'additional_spending_usd':0,'model_api_cost_usd':0,'paid_fallback':False,
            'commit':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),
            'status':'BLOCKED','experiments':[]}
    try:
        required={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'Ledgercorp/BountyForge',
                  'GITHUB_REF':'refs/heads/engineering/revenue-linux-scout-20261021',
                  'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','BOUNTYFORGE_PHASE13_QWEN_ACK':'true'}
        if any(os.environ.get(key)!=value for key,value in required.items()):
            raise ValueError('Explicit standard public Linux comparison required')
        require_credential_free_host()
        for protocol,factory in [('legacy_line_schema',LocalModel),('qwen_statement_schema_v2',None)]:
            service=RepairService(model_factory=factory)
            task=service.prepare('optional-setting','QWEN_LOCAL')
            result=service.run_qwen(task['task_id'],0)
            report['experiments'].append({'protocol':protocol,'result':result})
            if (type(result.get('model_calls')) is not int or not 1<=result['model_calls']<=2
                    or result.get('paid_fallback') is not False
                    or result.get('verification_receipt',{}).get('receipt_sha256')!=
                       receipt_hash(result.get('verification_receipt',{}))):
                raise ValueError('Comparison did not complete the shared verifier contract')
        report.update(status='COMPLETED',model_calls=sum(x['result']['model_calls'] for x in report['experiments']))
    except (RuntimeError,OSError,ValueError,TypeError,KeyError) as exc:
        report['blocking_reason']=type(exc).__name__
    finally:
        report['elapsed_seconds']=round(time.monotonic()-began,3)
        path=Path(opts.output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({key:report.get(key) for key in ('status','model_calls','elapsed_seconds')}))
    return 0 if report['status']=='COMPLETED' else 1


if __name__=='__main__':raise SystemExit(main())
