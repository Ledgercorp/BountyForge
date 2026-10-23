"""Native Codex MCP queue acceptance; replays existing candidates, no generation."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from scripts.codex_mcp_acceptance import CodexClient, _payload, _owned_child, EXPECTED

ROOT=Path(__file__).resolve().parents[1]


def main():
    report={'kind':'phase13_native_codex_queue_blackbox','new_model_generations':0,
            'accuracy_claim':False,'checks':{},'observations':[],'additional_spending_usd':0}
    started=time.monotonic();client=CodexClient(read_timeout=120);thread=client.thread()
    def call(tool,args):
        response=client.call(thread,tool,args)
        report['observations'].append({'tool':tool,'response':response})
        return _payload(response)
    def refused(tool,args):
        response=client.call(thread,tool,args)
        report['observations'].append({'tool':tool,'response':response})
        return 'error' in response or response.get('result',{}).get('isError') is True
    def lease(job,batch='phase13-blackbox'):
        return {'batch_id':batch,'job_id':job['job_id'],'lease_token':job['lease_token']}
    try:
        status=client.status(thread)['result']['data']
        server=next(row for row in status if row['name']=='bountyforge')
        report['checks']['exact_eighteen_tools']=set(server['tools'])==EXPECTED
        _,child=_owned_child(client.process.pid)
        report['checks']['path_only_environment']=child['environment_names']=={'PATH'}
        batch={'batch_id':'phase13-blackbox','engine':'CODEX_AGENT','case_ids':['chunk-count','optional-setting']}
        call('create_owned_queue',batch)
        report['checks']['duplicate_enqueue_idempotent']=call('create_owned_queue',batch)['created'] is False
        report['checks']['customer_source_refused']=refused('create_owned_queue',dict(batch,source='unapproved'))
        report['checks']['unknown_delivery_tool_refused']=refused('deliver_customer_patch',{})
        first=call('claim_owned_queue',{'batch_id':batch['batch_id']})
        report['checks']['single_active_worker']=call('claim_owned_queue',{'batch_id':batch['batch_id']})['outcome']=='WORKER_BUSY'
        report['checks']['heartbeat']=call('heartbeat_owned_queue',lease(first))['outcome']=='LEASE_RENEWED'
        report['checks']['arbitrary_path_refused']=refused('submit_owned_queue',dict(lease(first),revision=0,
            proposal={'changes':[{'line':4,'new':'return 0','path':'secret.py'}]}))
        one=call('submit_owned_queue',dict(lease(first),revision=0,proposal={'changes':[{'line':4,'new':'return 0'}]}))
        report['checks']['failed_tests_not_verified']=one['receipt']['outcome']=='TEST_FAILED' and one['state']=='LEASED'
        stale=call('submit_owned_queue',dict(lease(first),revision=0,proposal={'changes':[{'line':4,'new':'return 1'}]}))
        report['checks']['stale_revision_refused']=stale['outcome']=='STALE_REVISION'
        two=call('submit_owned_queue',dict(lease(first),revision=1,proposal={'changes':[{'line':4,'new':'import os'}]}))
        report['checks']['capability_patch_and_attempt_budget']=two['receipt']['outcome']=='SOURCE_REJECTED' and two['state']=='FAILED'
        interrupted=call('claim_owned_queue',{'batch_id':batch['batch_id']})
        # Kill only our MCP child. Persisted lease survives; no inference process exists.
        pid,_=_owned_child(client.process.pid);os.kill(pid,signal.SIGKILL)
        report['checks']['controlled_mcp_termination']=True
    finally:
        report['first_client_exit']=client.stop()
    client=CodexClient(read_timeout=120);thread=client.thread()
    try:
        status=call('owned_queue_status',{'batch_id':'phase13-blackbox'})
        report['checks']['restart_preserves_terminal_and_active_state']=[j['state'] for j in status['jobs']]==['FAILED','LEASED']
        lost=call('submit_owned_queue',dict(lease(interrupted),revision=0,proposal={'changes':[{'line':2,'new':'selected = value'}]}))
        report['checks']['restart_cannot_reuse_process_capability']=lost['outcome']=='SESSION_CAPABILITY_LOST'
        call('release_owned_queue',lease(interrupted))
        recovered=call('claim_owned_queue',{'batch_id':'phase13-blackbox'})
        report['checks']['recovery_uses_new_lease_and_preparation']=recovered['lease_token']!=interrupted['lease_token'] and recovered['task']['task_id']!=interrupted['task']['task_id']
        old=call('submit_owned_queue',dict(lease(interrupted),revision=0,proposal={'changes':[{'line':2,'new':'selected = value'}]}))
        report['checks']['old_writer_fenced_after_recovery']=old['outcome']=='STALE_EXPIRED_OR_REVOKED_LEASE'
        recording=json.loads((ROOT/'evidence/phase13/codex_queue_session.json').read_bytes())
        for entry in recording['calls']:
            if entry['tool']=='submit_owned_queue':
                value=json.loads(entry['response']['result']['content'][0]['text'])
                if value['receipt']['case_id']=='optional-setting':proposal=value['receipt']['proposal']
        fixed=call('submit_owned_queue',dict(lease(recovered),revision=0,proposal=proposal))
        report['checks']['recovered_candidate_requires_fresh_replay']=fixed['state']=='VERIFIED' and fixed['receipt']['independent']['passed'] is True
        stop_batch={'batch_id':'phase13-stop','engine':'CODEX_AGENT','case_ids':['inclusive-window']}
        call('create_owned_queue',stop_batch);stopped=call('claim_owned_queue',{'batch_id':'phase13-stop'})
        process=subprocess.run([sys.executable,'-m','scripts.owned_queue','stop','--batch-id','phase13-stop'],
                               cwd=ROOT,capture_output=True,text=True,timeout=10)
        report['checks']['separate_process_stop_control']=process.returncode==0 and json.loads(process.stdout)['outcome']=='STOPPED'
        stop_result=call('submit_owned_queue',dict(lease(stopped,'phase13-stop'),revision=0,proposal={'changes':[{'line':3,'new':'return []'}]}))
        report['checks']['stop_revokes_candidate_submission']=stop_result['outcome']=='STALE_EXPIRED_OR_REVOKED_LEASE'
        report['checks']['stopped_batch_cannot_reclaim']=call('claim_owned_queue',{'batch_id':'phase13-stop'})['outcome']=='STOPPED'
        call('create_owned_queue',{'batch_id':'phase13-qwen','engine':'QWEN_LOCAL','case_ids':['optional-setting']})
        qwen=call('claim_owned_queue',{'batch_id':'phase13-qwen'})
        mismatch=call('submit_owned_queue',dict(lease(qwen,'phase13-qwen'),revision=0,proposal=proposal))
        report['checks']['engine_identity_fenced']=mismatch['outcome']=='QUEUE_ENGINE_MISMATCH'
        inventory=call('list_repair_engines',{})['engines']
        if inventory[0]['availability']=='PINNED_LOCAL_RUNTIME_UNAVAILABLE':
            unavailable=call('run_owned_queue_qwen',lease(qwen,'phase13-qwen'))
            report['checks']['unavailable_qwen_no_inference_or_fallback']=(unavailable['state']=='BLOCKED'
                and unavailable['receipt']['model_calls']==0 and unavailable['receipt']['paid_fallback'] is False)
        else:raise RuntimeError('This model-free acceptance requires Qwen unavailable')
    finally:report['second_client_exit']=client.stop()
    report.update(all_checks_passed=all(report['checks'].values()),elapsed_seconds=round(time.monotonic()-started,3))
    (ROOT/'evidence/phase13/blackbox_acceptance.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'checks':len(report['checks']),'all_checks_passed':report['all_checks_passed'],
                      'new_model_generations':0,'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if report['all_checks_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
