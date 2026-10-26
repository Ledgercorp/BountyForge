"""Owned Linux acceptance only: reproduced baselines and deliberately bad inputs.

No model, remote provider, API credential, spending grant or reference solution.
"""
import argparse
import json
import resource
import time
from phase22_repair import OwnedSession,catalog
from phase22_run import write_receipt


def run():
    began=time.monotonic();cpu=time.process_time();service=OwnedSession();rows=[]
    for spec in catalog().tasks():
        task=service.prepare(spec['id'])
        rows.append({'case_id':spec['id'],'source_sha256':task['source_sha256'],
                     'tests_sha256':task['tests_sha256'],'baseline':service.sessions[spec['id']]['baseline']})
    # A deliberately incorrect, novel candidate (not a repair) and an identical
    # retry exercise the unchanged validator + actual Docker regression route.
    task=service.current('discount_checkout')
    bad=json.dumps({'changes':[{'line':9,'new':'discount = subtotal * rate'}]})
    wrong=service.submit(task,bad);duplicate=service.submit(service.current('discount_checkout'),bad)
    third_refused=False
    try:service.submit(service.current('discount_checkout'),bad)
    except ValueError:third_refused=True
    other=service.current('retry_state')
    outside=service.submit(other,json.dumps({'changes':[{'line':1,'new':'return 0'}]}))
    command=service.submit(service.current('retry_state'),json.dumps({'changes':[{'line':9,'new':'attempts = __import__("os").system("id")'}]}))
    correct=(len(rows)==6 and all(not r['baseline']['passed'] and r['baseline']['tests_run']==8 for r in rows)
             and wrong['outcome']=='TEST_FAILED' and wrong['targeted']['tests_run']==8
             and duplicate['outcome']=='REPEATED_PROPOSAL' and third_refused
             and outside['outcome']=='SOURCE_REJECTED' and command['outcome']=='SOURCE_REJECTED')
    return {'kind':'PHASE22_MODEL_FREE_LINUX_ACCEPTANCE','status':'PASSED' if correct else 'FAILED',
            'cases':rows,'runtime_admission':service.proof,'intentional_bad_proposal':wrong,'duplicate':duplicate,
            'third_submission_refused':third_refused,'unauthorized_anchor':outside,'command_proposal':command,
            'actual_inference_requests':0,'actual_model_generated_repairs':0,'reference_repairs_supplied':False,
            'model_accuracy':'UNMEASURED','provider':'NOT_USED','commercial_admission':'NOT_ADMITTED',
            'elapsed_seconds':round(time.monotonic()-began,3),'controller_cpu_seconds':round(time.process_time()-cpu,3),
            'controller_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'additional_cash_spending_usd':0,'existing_credit_spending_usd':0}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--admit-owned-model-free-checks',action='store_true',required=True)
    p.add_argument('--output',required=True);args=p.parse_args(argv)
    result=run();write_receipt(args.output,result)
    print(json.dumps({k:result[k] for k in ('status','actual_inference_requests','actual_model_generated_repairs')}))
    return 0 if result['status']=='PASSED' else 1


if __name__=='__main__':raise SystemExit(main())
