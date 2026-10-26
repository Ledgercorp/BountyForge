"""Crypto advertisements, not income or execution authority. No wallet actions."""
import hashlib
import json
import re
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
from bountyforge.qualification import qualify
from bountyforge.opportunities import _github_issue

USDC_SOLANA='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
ASSET_SOURCES={'USDC':'https://developers.circle.com/stablecoins/usdc-contract-addresses',
               'SOL':'https://solana.com/docs/core/fees'}
SCAM=re.compile(r'(?i)(pay a registration fee|deposit to unlock|buy tokens to qualify|send (?:us )?(?:your )?(?:seed phrase|private key))')


def amount(value,*,zero=False):
    if isinstance(value,bool) or not isinstance(value,(str,int,float,Decimal)):raise ValueError('DECIMAL_AMOUNT_REQUIRED')
    if type(value) is str and len(value)>64:raise ValueError('DECIMAL_AMOUNT_BOUND')
    try:n=Decimal(str(value))
    except InvalidOperation:raise ValueError('DECIMAL_AMOUNT_REQUIRED') from None
    if (not n.is_finite() or n<0 or (not zero and n==0) or n>Decimal('1000000000')
            or len(n.as_tuple().digits)>32 or n.as_tuple().exponent < -18):raise ValueError('AMOUNT_OUT_OF_BOUNDS')
    return format(n,'f')


def research_work_plan(item,qualification):
    """Return gated research steps; never assert a repair task is admitted."""
    if type(item) is not dict or type(qualification) is not dict:
        raise ValueError('NORMALIZED_OPPORTUNITY_AND_QUALIFICATION_REQUIRED')
    if qualification.get('execution_authorized') is not False or qualification.get('submission_authorized') is not False:
        raise ValueError('RESEARCH_PLAN_MUST_NOT_GRANT_AUTHORITY')
    return {'kind':'CRYPTO_RESEARCH_WORK_PLAN','opportunity_id':item.get('id'),'provider':item.get('provider'),
            'steps':[{'stage':'RECHECK_PRIMARY_LISTING','status':'BLOCKED_UNTIL_OWNER_AUTHORIZED_PROVIDER_ACCESS'},
                     {'stage':'VERIFY_FUNDING_AND_PAYOUT_TERMS','status':'UNVERIFIED'},
                     {'stage':'VERIFY_AI_AND_US_ELIGIBILITY','status':'UNVERIFIED'},
                     {'stage':'REVIEW_SOURCE_RIGHTS_AND_TEST_SAFETY','status':'NOT_ADMITTED'},
                     {'stage':'CREATE_BOUNDED_REPAIR_PLAN','status':'BLOCKED_UNTIL_SCOPE_AND_SOURCE_AUTHORIZED'},
                     {'stage':'INDEPENDENTLY_VERIFY_PATCH','status':'BLOCKED_UNTIL_HOSTILE_CODE_ADMISSION'},
                     {'stage':'OWNER_REVIEW_AND_SUBMISSION','status':'OWNER_APPROVAL_REQUIRED'}],
            'execution_authorized':False,'submission_authorized':False,'expected_net_usd':None}


def timestamp(text):
    if type(text) is not str:raise ValueError('TIMESTAMP_REQUIRED')
    try:r=datetime.fromisoformat(text.replace('Z','+00:00'))
    except ValueError:raise ValueError('TIMESTAMP_REQUIRED') from None
    if r.tzinfo is None:raise ValueError('AWARE_TIMESTAMP_REQUIRED')
    return r


def fresh(observed,now,seconds):
    try:age=(timestamp(now)-timestamp(observed)).total_seconds();return 0<=age<=seconds
    except ValueError:return False


def asset_identity(symbol,chain,address):
    return (symbol=='SOL' and chain=='solana-mainnet' and address in (None,'')) or (symbol=='USDC' and chain=='solana-mainnet' and address==USDC_SOLANA)


def canonical_url(url,provider):
    if type(url) is not str:raise ValueError('SOURCE_URL_REQUIRED')
    p=urlsplit(url);hosts={'superteam':{'superteam.fun'},'onlydust':{'app.onlydust.com','onlydust.com'},'github':{'github.com'},'immunefi':{'immunefi.com'}}
    if (provider not in hosts or p.scheme!='https' or p.hostname not in hosts[provider] or p.username or p.password
            or p.port not in (None,443) or p.query or p.fragment or '..' in p.path):raise ValueError('CANONICAL_PLATFORM_URL_REQUIRED')
    if provider=='github' and not _github_issue(url):raise ValueError('CANONICAL_GITHUB_ISSUE_REQUIRED')
    return url.rstrip('/')


def normalize_superteam(row,observed_at):
    if type(row) is not dict or type(row.get('id')) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}',row['id']):raise ValueError('LISTING_ID_REJECTED')
    slug=row.get('slug')
    if type(slug) is not str or not re.fullmatch(r'[a-zA-Z0-9_-]{1,180}',slug):raise ValueError('LISTING_SLUG_REJECTED')
    timestamp(observed_at)
    reward=None
    if row.get('rewardAmount') is not None:reward=amount(row['rewardAmount'])
    title=str(row.get('title',''))[:250];description=str(row.get('description',''))[:6000]
    skills=row.get('skills',[])
    if type(skills) is not list:skills=[]
    return {'schema':1,'provider':'superteam','id':row['id'],'source_url':canonical_url('https://superteam.fun/earn/listing/'+slug,'superteam'),
        'title':title,'requirements_untrusted':description,'observed_at':observed_at,'observation_kind':'PUBLIC_PROVIDER_RECORD',
        'advertised_amount':reward,'payment_asset':str(row.get('token') or 'UNKNOWN').upper()[:20],
        'payment_chain':None,'asset_address':None,'funding_status':'UNVERIFIED','funding_evidence':[],
        'compensation_type':row.get('compensationType','fixed'),'advertised_min':row.get('minRewardAsk'),'advertised_max':row.get('maxRewardAsk'),
        'deadline':row.get('deadline'),'availability':'CLOSED' if row.get('isWinnersAnnounced') is True else 'OPEN' if row.get('status')=='OPEN' else 'UNKNOWN',
        'ai_agent_eligibility':'ALLOWED' if row.get('agentAccess') in ('AGENT_ALLOWED','AGENT_ONLY') else 'HUMAN_ONLY' if row.get('agentAccess')=='HUMAN_ONLY' else 'UNKNOWN',
        'us_eligibility':'UNKNOWN','eligibility_evidence':[],'required_skills':[str(s)[:80] for s in skills[:20]],
        'complexity':'UNKNOWN','submission_requirements':'DETAILS_REVIEW_REQUIRED','acceptance_conditions':'SPONSOR_JUDGMENT_UNVERIFIED',
        'competition_count':row.get('_count',{}).get('Submission') if type(row.get('_count')) is dict else None,
        'transaction_fees':None,'withdrawal_fees':None,'legal_payout_route':'OWNER_REVIEW_REQUIRED',
        'collection_probability':None,'upfront_deposit_required':None,'scam_signal':bool(SCAM.search(title+' '+description)),
        'github_issue':None,'technical_profile':'PYTHON' if any('python' in str(s).lower() for s in skills) else 'UNKNOWN'}


def import_onlydust(row,observed_at):
    # No documented public API was established; an explicit export is evidence
    # for research only, never independently verified availability/AI/funding.
    if type(row) is not dict or set(row)-{'id','source_url','title','payment_asset','advertised_amount','description'}:
        raise ValueError('ONLYDUST_IMPORT_FIELDS_REJECTED')
    normalized=normalize_superteam({'id':row['id'],'slug':row['id'],'title':row.get('title',''),
        'token':row.get('payment_asset'),'rewardAmount':row.get('advertised_amount'),'description':row.get('description','')},observed_at)
    normalized.update(provider='onlydust',source_url=canonical_url(row['source_url'],'onlydust'),
                      observation_kind='EXPLICIT_IMPORT_NOT_LIVE_RECHECKED',availability='UNKNOWN',ai_agent_eligibility='UNKNOWN')
    return normalized


def normalize_github(row,observed_at):
    url=canonical_url(row.get('html_url'),'github');text=str(row.get('title',''))+' '+str(row.get('body',''))[:12000]
    matches=re.findall(r'(?i)\b([1-9][0-9]{0,6}(?:\.[0-9]{1,6})?)\s+(USDC|SOL|ETH|BTC)\b',text)
    if len(set((a,b.upper()) for a,b in matches))!=1:raise ValueError('UNAMBIGUOUS_CRYPTO_REWARD_REQUIRED')
    value,symbol=matches[0];ident=hashlib.sha256(url.encode()).hexdigest()
    record=normalize_superteam({'id':ident,'slug':ident,'title':row.get('title',''),'token':symbol,'rewardAmount':value,'description':row.get('body','')},observed_at)
    state=row.get('state')
    availability=('OPEN' if state.casefold()=='open' else 'CLOSED' if state.casefold()=='closed' else 'UNKNOWN') if type(state) is str else 'UNKNOWN'
    record.update(provider='github',source_url=url,github_issue=url,observation_kind='UNVERIFIED_SEARCH_CURRENCY_MATCH',currency_claim_amount=record['advertised_amount'],availability=availability,ai_agent_eligibility='UNKNOWN')
    if not re.search(r'(?i)\b(bounty|reward|paid (?:fix|task|bug))\b',str(row.get('title',''))):record['advertised_amount']=None
    return record


def qualify_crypto(item,*,now=None):
    now=now or datetime.now(timezone.utc).isoformat();reasons=[]
    if item.get('source_risk')=='KNOWN_AGGREGATOR':reasons.append('AGGREGATOR_NOT_PRIMARY_FUNDING_SOURCE')
    if item.get('observation_kind')=='UNVERIFIED_SEARCH_CURRENCY_MATCH':reasons.append('GITHUB_OFFER_ROLE_NOT_INDEPENDENTLY_VERIFIED')
    if item.get('scam_signal'):reasons.append('SCAM_OR_ADVANCE_PAYMENT_SIGNAL')
    if item.get('payment_asset') not in ('USDC','SOL','ETH','BTC'):reasons.append('UNADMITTED_TOKEN')
    if item.get('availability')=='CLOSED':reasons.append('CLOSED_OR_EXPIRED')
    elif item.get('availability')!='OPEN':reasons.append('AVAILABILITY_UNVERIFIED')
    try:
        if timestamp(item.get('deadline'))<=timestamp(now):reasons.append('CLOSED_OR_EXPIRED')
    except ValueError:reasons.append('DEADLINE_UNVERIFIED')
    if not fresh(item.get('observed_at'),now,86400):reasons.append('STALE_OR_UNKNOWN_OBSERVATION')
    if item.get('funding_status')!='INDEPENDENTLY_VERIFIED':reasons.append('FUNDING_UNVERIFIED')
    if item.get('ai_agent_eligibility')!='ALLOWED':reasons.append('AI_NOT_EXPLICITLY_ALLOWED')
    if item.get('us_eligibility')!='VERIFIED_ALLOWED':reasons.append('US_ELIGIBILITY_UNVERIFIED')
    if item.get('upfront_deposit_required') is not False:reasons.append('NO_UPFRONT_PAYMENT_UNVERIFIED')
    if not asset_identity(item.get('payment_asset'),item.get('payment_chain'),item.get('asset_address')):reasons.append('ASSET_NETWORK_IDENTITY_UNVERIFIED')
    if item.get('technical_profile')!='PYTHON':reasons.append('PYTHON_PROFILE_UNVERIFIED')
    if item.get('legal_payout_route')!='OWNER_VERIFIED':reasons.append('OWNER_PAYOUT_ROUTE_REQUIRED')
    # Existing qualification deliberately cannot attest deposited funding from
    # a listing. Reuse its independent safety/commercial gate, never bypass it.
    legacy=qualify({'language':'python' if item.get('technical_profile')=='PYTHON' else None})
    reasons+=['COMMERCIAL_NOT_ADMITTED','THIRD_PARTY_EXECUTION_NOT_ADMITTED','OWNER_SUBMISSION_APPROVAL_REQUIRED']
    return {'status':'QUARANTINED' if 'SCAM_OR_ADVANCE_PAYMENT_SIGNAL' in reasons or 'UNADMITTED_TOKEN' in reasons else 'BLOCKED',
            'reasons':sorted(set(reasons)),'legacy_gate':legacy.to_dict(),'execution_authorized':False,'submission_authorized':False,
            'research_priority':0 if item.get('scam_signal') or 'CLOSED_OR_EXPIRED' in reasons else 2 if item.get('technical_profile')=='PYTHON' and item.get('availability')=='OPEN' else 1,
            'commercial_admission':'NOT_ADMITTED'}


def profitability(item,quote=None,*,now=None):
    now=now or datetime.now(timezone.utc).isoformat();gross=None
    if quote and quote.get('usd_price') is not None and quote.get('asset')==item.get('payment_asset') and fresh(quote.get('observed_at'),now,900) and item.get('advertised_amount') is not None:
        gross=amount(Decimal(amount(item['advertised_amount']))*Decimal(amount(quote.get('usd_price'))))
    return {'advertised_gross_usd':gross,'conversion_observed_at':quote.get('observed_at') if gross else None,
            'quote_venue':quote.get('venue') if gross else None,'quote_is_cash_realization':False,
            'liquidity_observation':quote.get('volume_24h') if gross else None,
            'completion_probability':None,'acceptance_probability':None,'collection_probability':None,
            'coding_cost_usd':None,'verification_cost_usd':None,'engineering_hours':None,
            'withdrawal_fees_usd':None,'expected_net_usd':None,'guaranteed_income':False,
            'ranking_basis':'RESEARCH_PRIORITY_ONLY_UNTIL_CALIBRATED_PROBABILITIES_COSTS_AND_FUNDING_EXIST'}


def deduplicate(items):
    grouped={}
    for item in items:
        key=item.get('github_issue') or item['provider']+':'+item['id'];grouped.setdefault(key,[]).append(item)
    out=[]
    for key,rows in grouped.items():
        distinct={}
        for row in rows:
            fingerprint=json.dumps({k:v for k,v in row.items() if k!='observed_at'},sort_keys=True,allow_nan=False)
            distinct.setdefault(fingerprint,row)
        out.append({'coordination_key':hashlib.sha256(key.encode()).hexdigest(),'coordination_status':'UNIQUE' if len(distinct)==1 else 'CONFLICTING_DUPLICATES','duplicate_observations':len(rows),'records':list(distinct.values())})
    return sorted(out,key=lambda r:r['coordination_key'])
