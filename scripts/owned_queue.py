"""Owner controls for the local owned-only queue. No background Codex launcher."""
import argparse
import json
from bountyforge.owned_repair_queue import OwnedRepairQueue


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['create','status','stop','run-qwen'])
    parser.add_argument('--batch-id',required=True)
    parser.add_argument('--engine',choices=['QWEN_LOCAL','CODEX_AGENT'])
    parser.add_argument('--case-id',action='append',default=[])
    opts=parser.parse_args(argv)
    try:
        queue=OwnedRepairQueue()
        if opts.action=='create':result=queue.create(opts.batch_id,opts.engine,opts.case_id)
        elif opts.engine or opts.case_id:raise ValueError('Create arguments only')
        elif opts.action=='status':result=queue.status(opts.batch_id)
        elif opts.action=='stop':result=queue.stop(opts.batch_id)
        else:
            if queue.status(opts.batch_id)['engine']!='QWEN_LOCAL':
                result={'outcome':'ACTIVE_CODEX_SESSION_REQUIRED','model_calls':0,'paid_fallback':False}
                print(json.dumps(result));return 2
            for _ in range(5):
                job=queue.claim(opts.batch_id)
                if 'lease_token' not in job:
                    print(json.dumps(job),flush=True);break
                result=queue.run_qwen(opts.batch_id,job['job_id'],job['lease_token'])
                print(json.dumps(result),flush=True)
                if result['state']=='BLOCKED':break
            result=queue.status(opts.batch_id)
        print(json.dumps(result,sort_keys=True,allow_nan=False));return 0
    except (ValueError,RuntimeError,OSError):
        print(json.dumps({'outcome':'OWNED_QUEUE_CONTROL_REJECTED','paid_fallback':False}));return 2


if __name__=='__main__':raise SystemExit(main())
