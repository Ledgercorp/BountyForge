"""Actual Codex-MCP failure/recovery acceptance, not model-accuracy sampling."""
import json
from pathlib import Path
import time

from scripts.codex_mcp_acceptance import CodexClient, _payload, _owned_child

ROOT=Path(__file__).resolve().parents[1]


def main():
    report={'kind':'phase12_codex_mcp_boundary_acceptance','new_model_generations':0,
            'reuses_already_recorded_candidate':True,'accuracy_claim':False,'checks':{},'receipts':[]}
    began=time.monotonic();client=CodexClient(read_timeout=120)
    def call(name,args):return client.call(thread,name,args)
    def refused(name,args):
        result=call(name,args)
        return 'error' in result or result.get('result',{}).get('isError') is True
    try:
        thread=client.thread();_,child=_owned_child(client.process.pid)
        report['checks']['path_only_child_environment']=child['environment_names']=={'PATH'}
        inventory=_payload(call('list_repair_engines',{}))['engines']
        report['engine_inventory']=inventory
        task=_payload(call('prepare_owned_repair',{'case_id':'weighted-mix','engine':'CODEX_AGENT'}))
        token=task['task_id']
        bad={'changes':[{'line':4,'new':'denominator = 123'}]}
        first=_payload(call('submit_owned_repair',{'task_id':token,'revision':0,'proposal':bad}))
        report['receipts'].append(first)
        report['checks']['wrong_logic_not_review_ready']=first['outcome']=='TEST_FAILED' and not first['independently_verified']
        report['checks']['stale_revision_refused']=refused('submit_owned_repair',{'task_id':token,'revision':0,'proposal':bad})
        recording=json.loads((ROOT/'evidence/phase12/codex_live_repairs.json').read_bytes())
        proposal=None
        for entry in recording['calls']:
            result=entry['response'].get('result',{})
            if result.get('isError') is False:
                value=json.loads(result['content'][0]['text'])
                if value.get('case_id')=='weighted-mix' and value.get('outcome')=='VERIFIED':proposal=value['proposal']
        assert proposal is not None
        fixed=_payload(call('submit_owned_repair',{'task_id':token,'revision':1,'proposal':proposal}))
        report['receipts'].append(fixed)
        report['checks']['bounded_revision_and_fresh_replay']=fixed['independently_verified'] and fixed['attempt']==2 and fixed['previous_receipt_sha256']==first['receipt_sha256']
        report['checks']['completed_task_cannot_resubmit']=refused('submit_owned_repair',{'task_id':token,'revision':1,'proposal':proposal})
        report['checks']['arbitrary_paths_refused']=refused('submit_owned_repair',{'task_id':token,'revision':1,'proposal':proposal,'path':'other.py'})
        report['checks']['unauthorized_delivery_refused']=refused('deliver_customer_patch',{'task_id':token})
        report['checks']['customer_source_refused']=refused('prepare_owned_repair',{'case_id':'weighted-mix','engine':'CODEX_AGENT','source':'unapproved'})
        probe=_payload(call('prepare_owned_repair',{'case_id':'weighted-mix','engine':'CODEX_AGENT'}))
        ineffective=_payload(call('submit_owned_repair',{'task_id':probe['task_id'],'revision':0,
                                 'proposal':{'changes':[{'line':4,'new':'denominator = len(pairs)'}]}}))
        invalid=_payload(call('submit_owned_repair',{'task_id':probe['task_id'],'revision':1,
                             'proposal':{'changes':[{'line':4,'new':'import os'}]}}))
        report['receipts'].extend([ineffective,invalid])
        report['checks']['ineffective_patch_rejected']=ineffective['outcome']=='SOURCE_REJECTED' and 'ineffective' in ineffective['diagnostic']
        report['checks']['capability_patch_rejected']=invalid['outcome']=='SOURCE_REJECTED' and invalid['state']=='EXHAUSTED'
        report['checks']['attempt_budget_enforced']=refused('submit_owned_repair',{'task_id':probe['task_id'],'revision':1,'proposal':proposal})
        qwen=_payload(call('prepare_owned_repair',{'case_id':'weighted-mix','engine':'QWEN_LOCAL'}))
        report['checks']['engine_separation_enforced']=refused('submit_owned_repair',{'task_id':qwen['task_id'],'revision':0,'proposal':proposal})
        if inventory[0]['availability']=='PINNED_LOCAL_RUNTIME_UNAVAILABLE':
            unavailable=_payload(call('run_owned_qwen',{'task_id':qwen['task_id'],'revision':0}))
            report['qwen_unavailable_response']=unavailable
            report['checks']['unavailable_qwen_has_no_fallback']=unavailable['outcome']=='QWEN_UNAVAILABLE' and unavailable['model_calls']==0 and unavailable['paid_fallback'] is False
        else:
            report['qwen_runtime_probe']='Available runtime not invoked during this model-free acceptance'
    finally:
        report['client_exit']=client.stop()
    restarted=CodexClient(read_timeout=120)
    try:
        fresh=restarted.thread()
        response=restarted.call(fresh,'submit_owned_repair',{'task_id':token,'revision':1,'proposal':proposal})
        report['checks']['restart_invalidates_process_local_capability']=response.get('result',{}).get('isError') is True
    finally:report['restarted_client_exit']=restarted.stop()
    report.update(all_checks_passed=all(report['checks'].values()),elapsed_seconds=round(time.monotonic()-began,3))
    (ROOT/'evidence/phase12/blackbox_acceptance.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'all_checks_passed':report['all_checks_passed'],'checks':len(report['checks']),
                      'new_model_generations':0,'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if report['all_checks_passed'] else 1

if __name__=='__main__':raise SystemExit(main())
