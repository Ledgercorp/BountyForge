"""Read-only crypto discovery and explicit inactive commercial rehearsal."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import hashlib
import hmac
from bountyforge.crypto_discovery import CryptoReadOnly
from bountyforge.crypto_opportunities import normalize_superteam,qualify_crypto,profitability,deduplicate,research_work_plan
from bountyforge.crypto_revenue import (CryptoLedger,CryptoReviewStore,ResearchQueue,submission_preview,verify_owner_review,submit_external)
from bountyforge.repair_engines import encoded,receipt_hash


def rehearsal(root):
    now=datetime.now(timezone.utc).isoformat()
    o=normalize_superteam({'id':'owned-simulation','slug':'owned-simulation','title':'OWNED PROTOCOL SIMULATION',
        'rewardAmount':100,'token':'USDC','deadline':'2099-01-01T00:00:00Z','agentAccess':'AGENT_ALLOWED','status':'OPEN','skills':['Python']},now)
    o['observation_kind']='OWNED_SIMULATOR_NOT_A_REAL_LISTING'
    q=ResearchQueue(root/'research.sqlite');added=q.enqueue_opportunity(o);duplicate=not q.enqueue_opportunity(o)
    first=q.claim(5);stale_refused=None
    if first:
        q.conn.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(first['id'],));second=q.claim(5)
        stale_refused=not q.finish(first['id'],{'status':'failed','reason':'QUALIFICATION_BLOCKED'},lease_token=first['lease_token'])
        q.finish(second['id'],{'status':'failed','reason':'QUALIFICATION_BLOCKED_NO_REPAIR_EXECUTION'},lease_token=second['lease_token'])
    q.close()
    store=CryptoReviewStore(root/'crypto.sqlite');ledger=CryptoLedger(store,mode='SIMULATED')
    ledger.record_status('owned-simulation','AWARDED_REPORTED','USDC','100',source=o['source_url'])
    proof={'kind':'SOLANA_FINALIZED_NET_RECEIPT','signature':'3'*88,'wallet':'2'*32,'asset':'USDC','amount_base_units':1000000,'decimals':6,'slot':10}
    ledger.record_simulated_payment('owned-simulation',proof)
    payment_duplicate=not ledger.record_simulated_payment('owned-simulation',proof)
    package=submission_preview(o,{'classification':'OWNED_DEVELOPMENT','independently_verified':True},now=now)
    # Explicit simulation-only APPLICATION review key, not a financial wallet key.
    key=b'OWNED_SIMULATION_APPLICATION_REVIEW_KEY_ONLY'
    payload={'purpose':'BOUNTYFORGE_SUBMISSION_REVIEW','package_sha256':package['package_sha256'],'opportunity_id':o['id'],'expires_unix':2000000000}
    approval={'payload':payload,'signature':hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()}
    review=verify_owner_review(package,approval,key)
    refused=False
    try:submit_external(package,approval,key)
    except ValueError:refused=True
    summary=CryptoLedger(CryptoReviewStore(root/'crypto.sqlite'),mode='SIMULATED').summary()
    ok=(duplicate and payment_duplicate and review and refused and summary['confirmed_real_earnings_usd']=='0'
        and summary['simulated_received_assets']=={'USDC':'1'} and (stale_refused is True or not added))
    return {'kind':'PHASE25_OWNED_COMMERCIAL_REHEARSAL','status':'PASSED' if ok else 'FAILED','simulation_only':True,
            'opportunity_is_fictional':True,'signature_is_simulated':True,'application_review_is_simulated':True,
            'duplicate_queue_entry_prevented':duplicate,'duplicate_payment_prevented':payment_duplicate,
            'stale_lease_finish_refused':stale_refused,'restarted_existing_state':not added,'external_submission_refused':refused,
            'qualification':qualify_crypto(o,now=now),'submission_preview':package,'earnings':summary,
            'real_submissions':0,'real_payments':0,'wallet_actions':0,'actual_inference_requests':0,
            'network_requests':0,'commercial_admission':'NOT_ADMITTED'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    discover=sub.add_parser('discover');discover.add_argument('--admit-public-reads',action='store_true',required=True);discover.add_argument('--output',type=Path,required=True)
    simulate=sub.add_parser('rehearse');simulate.add_argument('--admit-owned-simulation',action='store_true',required=True);simulate.add_argument('--state-dir',type=Path);simulate.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='status':
        print(json.dumps({'commercial_admission':'NOT_ADMITTED','paid_requests_authorized':0,'third_party_execution_authorized':False,
            'live_submissions_implemented':False,'wallet_actions_implemented':False,'scheduling_active':False,'confirmed_project_earnings_usd':'0'}));return 0
    if args.command=='discover':
        c=CryptoReadOnly();feed=c.discover();github=c.discover_github();algora=c.discover_github(algora_bot=True)
        quotes=[c.market_quote(a) for a in ('SOL','USDC')]
        sources=(feed,github,algora)
        source_rows=[x for source in sources for x in (source.get('opportunities') or [])]
        r={'kind':'BOUNTYFORGE_CRYPTO_READ_ONLY_SCAN','feed':feed,'github_search':github,
           'algora_github_search':algora,'quotes':quotes,'opportunities':[],
           'paid_requests':0,'external_writes':0,'scheduling_active':False,'complete_scan':False,'commercial_admission':'NOT_ADMITTED'}
        now=datetime.now(timezone.utc).isoformat();rows=[]
        for o in source_rows:
            gate=qualify_crypto(o,now=now)
            rows.append({**o,'qualification':gate,'research_plan':research_work_plan(o,gate),
                'profitability':profitability(o,next((q for q in quotes if q['asset']==o['payment_asset']),None),now=now)})
        r['opportunities']=deduplicate(rows)
        r['source_summary']={'github_candidates':len(github.get('opportunities') or []),
            'algora_bot_comment_candidates':len(algora.get('opportunities') or []),
            'superteam_candidates':len(feed.get('opportunities') or []),
            'github_authenticated':github.get('authenticated',False) or algora.get('authenticated',False),
            'all_sources_complete':False,'public_query_is_exhaustive':False}
    else:
        if args.state_dir:r=rehearsal(args.state_dir)
        else:
            with tempfile.TemporaryDirectory(prefix='bf-owned-crypto-rehearsal-') as tmp:r=rehearsal(Path(tmp))
    r['receipt_sha256']=receipt_hash(r);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:r[k] for k in ('kind','status','simulation_only','real_submissions','real_payments','actual_inference_requests') if k in r}))
    return 1 if r.get('status')=='FAILED' else 0


if __name__=='__main__':raise SystemExit(main())
