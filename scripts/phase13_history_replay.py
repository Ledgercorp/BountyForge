"""Real Docker verification and durable history, using an already recorded patch."""
import json
from pathlib import Path
import tempfile
from bountyforge.owned_repair_queue import OwnedRepairQueue
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import digest

ROOT=Path(__file__).resolve().parents[1]


def main():
    require_credential_free_host()
    raw=(ROOT/'evidence/phase13/codex_queue_session.json').read_bytes()
    if digest(raw)!='42a7be644b2f566276f1205959aa25600f5a26bc23e69f440ba3210d68f5b488':
        raise ValueError('Recorded candidate source changed')
    for call in json.loads(raw)['calls']:
        if call['tool']=='submit_owned_queue':
            value=json.loads(call['response']['result']['content'][0]['text'])
            if value['receipt']['case_id']=='optional-setting':proposal=value['receipt']['proposal']
    report={'kind':'phase13_durable_attempt_history_docker_acceptance',
            'new_model_generations':0,'recorded_candidate_replay_only':True,
            'accuracy_claim':False,'additional_spending_usd':0,'checks':{}}
    with tempfile.TemporaryDirectory(prefix='bf-owned-history-') as directory:
        path=Path(directory)/'private'/'queue.sqlite3';queue=OwnedRepairQueue(path)
        queue.create('history','CODEX_AGENT',['optional-setting']);job=queue.claim('history')
        first=queue.submit('history',job['job_id'],job['lease_token'],0,
                           {'changes':[{'line':2,'new':'selected = fallback'}]})
        second=queue.submit('history',job['job_id'],job['lease_token'],1,proposal)
        restarted=OwnedRepairQueue(path);status=restarted.status('history')
        history=status['jobs'][0]['attempt_history']
        report['receipts']=[first['receipt'],second['receipt']]
        report['restarted_status']=status
        report['checks']={'wrong_logic_failed':first['receipt']['outcome']=='TEST_FAILED',
                          'recorded_candidate_verified':second['state']=='VERIFIED',
                          'both_receipts_retained':len(history)==2 and [row['receipt_sha256'] for row in history]==
                             [first['receipt']['receipt_sha256'],second['receipt']['receipt_sha256']]}
        with restarted._db() as db:
            db.execute('UPDATE owned_attempt_receipts SET result=? WHERE reserved_through=1',('{}',))
        try:restarted.status('history');report['checks']['corruption_refused']=False
        except ValueError as exc:report['checks']['corruption_refused']=str(exc)=='QUEUE_HISTORY_CORRUPT'
    report['all_checks_passed']=all(report['checks'].values())
    (ROOT/'evidence/phase13/history_replay.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'all_checks_passed':report['all_checks_passed'],'checks':len(report['checks']),
                      'new_model_generations':0}))
    return 0 if report['all_checks_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
