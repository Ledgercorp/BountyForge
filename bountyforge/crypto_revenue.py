"""Private research/review bookkeeping, not commercial execution or custody.

Reuses existing SQLite privacy/CAS foundations and lease-fenced Queue. Network
submission is deliberately absent. HMAC review keys are application credentials,
never cryptocurrency signing/private wallet keys.
"""
import copy
from contextlib import closing
import hashlib
import hmac
import json
import re
import time
from decimal import Decimal
from pathlib import Path
from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.queue import Queue
from bountyforge.repair_engines import encoded,receipt_hash,strict_json
from bountyforge.crypto_opportunities import amount,canonical_url,fresh
from bountyforge.crypto_receipts import SolanaReadOnly,identity


def _state(value):
    if (type(value) is not dict or set(value)!={'version','mode','events','payments','costs'} or type(value['version']) is not int or value['version']!=1
            or value['mode'] not in ('SIMULATED','OBSERVE_ONLY') or type(value['events']) is not list or len(value['events'])>500
            or type(value['payments']) is not list or len(value['payments'])>100 or type(value['costs']) is not list or len(value['costs'])>100):raise ValueError('CRYPTO_REVIEW_STATE_REJECTED')
    seen=set()
    for p in value['payments']:
        if (type(p) is not dict or type(p.get('simulated')) is not bool
                or p['simulated']!=(value['mode']=='SIMULATED') or p.get('id') in seen
                or p.get('current_confirmation') not in ('FINALIZED','UNCONFIRMED_OR_UNAVAILABLE')):
            raise ValueError('PAYMENT_NAMESPACE_OR_IDENTITY_REJECTED')
        r=p.get('receipt',{})
        if (r.get('asset') not in ('SOL','USDC') or type(r.get('amount_base_units')) is not int or r['amount_base_units']<=0
                or r.get('decimals')!=(9 if r['asset']=='SOL' else 6)
                or p.get('id')!=hashlib.sha256(encoded([r.get('signature'),r.get('wallet'),r.get('asset')])).hexdigest()):raise ValueError('PAYMENT_CUSTODY_REJECTED')
        seen.add(p['id'])
    if len(encoded(value))>500000:raise ValueError('CRYPTO_REVIEW_STATE_BOUND')


class CryptoReviewStore(SQLitePaidReviewStore):
    def __init__(self,path):
        super().__init__(path)
        with closing(self._connect()) as c:
            c.execute('CREATE TABLE IF NOT EXISTS crypto_review_state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)');c.commit()

    def read_crypto(self):
        with closing(self._connect()) as c:r=c.execute('SELECT revision,payload FROM crypto_review_state WHERE id=1').fetchone()
        if r is None:return None,None
        if len(r[1])>500000:raise ValueError('CRYPTO_STATE_TOO_LARGE')
        state=strict_json(r[1]);_state(state);return state,str(r[0])

    def write_crypto(self,state,revision):
        _state(state);raw=encoded(state).decode()
        with closing(self._connect()) as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT revision FROM crypto_review_state WHERE id=1').fetchone()
            current=str(r[0]) if r else None
            if current!=revision:c.rollback();return False
            next_revision=(r[0] if r else 0)+1
            c.execute('INSERT INTO crypto_review_state VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload',(next_revision,raw));c.commit();return True


class CryptoLedger:
    def __init__(self,store,*,mode='OBSERVE_ONLY',owner_review_key=None):
        if type(store) is not CryptoReviewStore or mode not in ('SIMULATED','OBSERVE_ONLY'):raise ValueError('PRIVATE_CRYPTO_REVIEW_STORE_REQUIRED')
        self.store=store;self.mode=mode;self._review_key=owner_review_key
        state,revision=store.read_crypto()
        if state is None:
            if not store.write_crypto({'version':1,'mode':mode,'events':[],'payments':[],'costs':[]},None):raise ValueError('CRYPTO_CAS_CONFLICT')
        elif state['mode']!=mode:raise ValueError('SIMULATED_AND_REAL_STATE_MUST_REMAIN_SEPARATE')

    def _save(self,state,revision):
        if not self.store.write_crypto(state,revision):raise ValueError('CRYPTO_CAS_CONFLICT')

    def record_status(self,opportunity,stage,asset,value,*,source):
        if (type(opportunity) is not str or not re.fullmatch('[A-Za-z0-9_:-]{1,180}',opportunity)
                or stage not in ('PROJECTED','SUBMITTED_REPORTED','PENDING_DECISION','ACCEPTED_REPORTED','AWARDED_REPORTED','REJECTED_REPORTED','CANCELLED_REPORTED')
                or asset not in ('USDC','SOL','ETH','BTC')):raise ValueError('REPORTED_REWARD_FIELDS_REJECTED')
        source=canonical_url(source,'superteam' if 'superteam.fun/' in source else 'onlydust' if 'onlydust.com/' in source else 'github')
        event={'opportunity_id':opportunity,'stage':stage,'asset':asset,'amount':amount(value,zero=True),
               'source':source,'verified_payment':False,'actual_submission_attested':False}
        event['id']=hashlib.sha256(encoded(event)).hexdigest()
        state,revision=self.store.read_crypto()
        if any(e['id']==event['id'] for e in state['events']):return False
        event['observed_at_unix']=int(time.time())
        state['events'].append(event);self._save(state,revision);return True

    def _record_receipt(self,opportunity,proof,*,simulated):
        required={'kind','signature','wallet','asset','amount_base_units','decimals','slot'}
        if (type(proof) is not dict or not required<=set(proof) or proof['kind']!='SOLANA_FINALIZED_NET_RECEIPT'
                or proof['asset'] not in ('SOL','USDC') or type(proof['amount_base_units']) is not int or proof['amount_base_units']<=0
                or proof['decimals']!=(9 if proof['asset']=='SOL' else 6)):raise ValueError('FINALIZED_NET_RECEIPT_REQUIRED')
        identity(proof['signature'],'signature');identity(proof['wallet'],'wallet')
        key=hashlib.sha256(encoded([proof['signature'],proof['wallet'],proof['asset']])).hexdigest()
        state,revision=self.store.read_crypto()
        if any(p['id']==key for p in state['payments']):return False
        state['payments'].append({'id':key,'opportunity_id':opportunity,'status':'SIMULATED_RECEIVED' if simulated else 'OBSERVED_FINALIZED',
                                  'simulated':simulated,'receipt':{k:proof[k] for k in required},'current_confirmation':'FINALIZED',
                                  'owner_control_basis':'SIMULATION_ONLY' if simulated else 'SIGNED_OWNER_REVIEW_NOT_WALLET_SIGNATURE',
                                  'spendable_usd':None,'observations':[proof.get('receipt_sha256')]})
        self._save(state,revision);return True

    def record_simulated_payment(self,opportunity,proof):
        if self.mode!='SIMULATED':raise ValueError('SIMULATION_NAMESPACE_REQUIRED')
        if type(proof) is not dict or set(proof)-{'kind','signature','wallet','asset','amount_base_units','decimals','slot'}:
            raise ValueError('SIMULATED_RECEIPT_FIELDS_REJECTED')
        return self._record_receipt(opportunity,proof,simulated=True)

    def record_payment(self,opportunity,verifier,signature,asset,binding):
        if self.mode!='OBSERVE_ONLY' or type(verifier) is not SolanaReadOnly:raise ValueError('LIVE_READ_ONLY_VERIFIER_REQUIRED')
        wallet=verify_wallet_binding(binding,self._review_key)
        proof=verifier.verify(signature,wallet,asset)
        if proof['receipt_sha256']!=receipt_hash(proof):raise ValueError('VERIFIER_RECEIPT_IDENTITY_CHANGED')
        return self._record_receipt(opportunity,proof,simulated=False)

    def recheck_payment(self,payment_id,verifier):
        if self.mode!='OBSERVE_ONLY' or type(verifier) is not SolanaReadOnly:raise ValueError('LIVE_READ_ONLY_VERIFIER_REQUIRED')
        state,revision=self.store.read_crypto();p=next((p for p in state['payments'] if p['id']==payment_id),None)
        if p is None or p['simulated']:raise ValueError('KNOWN_OBSERVED_PAYMENT_REQUIRED')
        old=p['receipt']
        try:
            now=verifier.verify(old['signature'],old['wallet'],old['asset'])
            if now['amount_base_units']!=old['amount_base_units']:raise ValueError('CHAIN_RECEIPT_CHANGED')
            p['current_confirmation']='FINALIZED';p['observations'].append(now['receipt_sha256'])
        except ValueError:
            # Missing data may mean pruning/outage, not a proven reorg. Preserve
            # history, exclude uncertain payment from current confirmation.
            p['current_confirmation']='UNCONFIRMED_OR_UNAVAILABLE';p['observations'].append(None)
        self._save(state,revision)

    def record_cost(self,label,value,evidence_sha256,*,basis='ESTIMATED_UPPER'):
        if (type(label) is not str or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',label)
                or basis not in ('ESTIMATED_UPPER','DISPLAYED_ACCOUNT_DECREASE') or type(evidence_sha256) is not str
                or not re.fullmatch('[a-f0-9]{64}',evidence_sha256)):raise ValueError('COST_EVIDENCE_REJECTED')
        state,revision=self.store.read_crypto();row={'label':label,'amount_usd':amount(value,zero=True),'basis':basis,
            'evidence_sha256':evidence_sha256,'provider_invoiced_exact_cost':False}
        if row in state['costs']:return False
        state['costs'].append(row);self._save(state,revision);return True

    def summary(self):
        state,_=self.store.read_crypto();awards={};received={};simulated={};latest={}
        for event in state['events']:
            latest[(event['source'],event['opportunity_id'])]=event
        for event in latest.values():
            if event['stage']=='AWARDED_REPORTED':awards[event['asset']]=awards.get(event['asset'],Decimal(0))+Decimal(event['amount'])
        for payment in state['payments']:
            if payment['current_confirmation']!='FINALIZED':continue
            row=payment['receipt'];bucket=simulated if payment['simulated'] else received
            bucket[row['asset']]=bucket.get(row['asset'],Decimal(0))+Decimal(row['amount_base_units'])/(Decimal(10)**row['decimals'])
        return {'mode':self.mode,'reported_awards':{k:format(v,'f') for k,v in awards.items()},
                'received_assets':{k:format(v,'f') for k,v in received.items()},'simulated_received_assets':{k:format(v,'f') for k,v in simulated.items()},
                'confirmed_real_earnings_usd':'0' if not received else None,'net_realized_usd':None,'actual_operating_cost_usd':None,'cost_observations':state['costs'],
                'spendable_usd':None,'owner_withdrawal_route_verified':False,'wallet_balance_verified':False,
                'commercial_admission':'NOT_ADMITTED','actual_submissions_verified':0,'local_storage_cross_workspace_durable':False}


def _verify(envelope,key,purpose):
    if (type(key) is not bytes or len(key)<32 or type(envelope) is not dict or set(envelope)!={'payload','signature'}
            or type(envelope['payload']) is not dict or envelope['payload'].get('purpose')!=purpose
            or type(envelope['payload'].get('expires_unix')) is not int or envelope['payload']['expires_unix']<=time.time()
            or type(envelope['signature']) is not str or not hmac.compare_digest(envelope['signature'],hmac.new(key,encoded(envelope['payload']),hashlib.sha256).hexdigest())):
        raise ValueError('EXPLICIT_SIGNED_OWNER_REVIEW_REQUIRED')
    return envelope['payload']


def verify_wallet_binding(binding,key):
    payload=_verify(binding,key,'BOUNTYFORGE_PUBLIC_WALLET_BINDING')
    if set(payload)!={'purpose','expires_unix','wallet','network'} or payload['network']!='solana-mainnet':raise ValueError('WALLET_BINDING_REJECTED')
    return identity(payload['wallet'],'wallet')


def submission_preview(opportunity,repair_receipt=None,*,now):
    blockers=['COMMERCIAL_NOT_ADMITTED','HOSTILE_CODE_EXECUTION_NOT_ADMITTED','OWNER_SUBMISSION_APPROVAL_REQUIRED']
    if not fresh(opportunity.get('observed_at'),now,3600) or opportunity.get('availability')!='OPEN':blockers.append('FRESH_OPEN_LISTING_REQUIRED')
    if opportunity.get('ai_agent_eligibility')!='ALLOWED':blockers.append('AI_PERMISSION_REQUIRED')
    if repair_receipt and repair_receipt.get('classification')=='OWNED_DEVELOPMENT':blockers.append('OWNED_FIXTURE_IS_NOT_REAL_ASSIGNMENT')
    else:blockers.append('VERIFIED_AUTHORIZED_TARGET_REPAIR_REQUIRED')
    result={'kind':'CRYPTO_SUBMISSION_DRY_RUN','opportunity_id':opportunity['id'],'provider':opportunity['provider'],
            'source_url':canonical_url(opportunity['source_url'],opportunity['provider']),'blockers':blockers,
            'opportunity_snapshot_sha256':hashlib.sha256(encoded(opportunity)).hexdigest(),
            'repair_receipt_sha256':repair_receipt.get('receipt_sha256') if repair_receipt else None,
            'state':'PREPARED_DRY_RUN_NOT_SUBMITTABLE','submission_authorized':False,'external_dispatch_implemented':False,
            'commercial_admission':'NOT_ADMITTED','authorship_preserved_without_relabeling':True,'actual_submission_count':0}
    result['package_sha256']=hashlib.sha256(encoded(result)).hexdigest();return result


def verify_owner_review(package,approval,key):
    if package.get('package_sha256')!=hashlib.sha256(encoded({k:v for k,v in package.items() if k!='package_sha256'})).hexdigest():raise ValueError('PACKAGE_CONTENT_CHANGED')
    payload=_verify(approval,key,'BOUNTYFORGE_SUBMISSION_REVIEW')
    if (set(payload)!={'purpose','expires_unix','package_sha256','opportunity_id'}
            or payload['package_sha256']!=package['package_sha256'] or payload['opportunity_id']!=package['opportunity_id']):raise ValueError('REVIEW_SCOPE_CHANGED')
    return True


def submit_external(package,approval,key):
    verify_owner_review(package,approval,key)
    raise ValueError('COMMERCIAL_NOT_ADMITTED_NO_EXTERNAL_DISPATCH')


class ResearchQueue(Queue):
    def __init__(self,path):
        # Reuse existing private path protection, then unchanged fenced leases.
        SQLitePaidReviewStore(Path(path));super().__init__(path)

    def enqueue_opportunity(self,item):
        payload={'kind':'CRYPTO_RESEARCH_ONLY','provider':item['provider'],'id':item['id'],
                 'source_url':canonical_url(item['source_url'],item['provider']),'repair_execution_authorized':False,'commercial_admission':'NOT_ADMITTED'}
        key='crypto-'+hashlib.sha256(encoded(payload)).hexdigest()
        return self.enqueue(key,payload)

    def finish(self,job_id,result,*,lease_token):
        if result.get('status')!='failed':raise ValueError('RESEARCH_QUEUE_CANNOT_PROMOTE_TO_REPAIR_READY')
        return super().finish(job_id,result,lease_token=lease_token)
