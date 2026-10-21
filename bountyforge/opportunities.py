"""Evidence-conservative bounty selection and de-duplication.

Platform listings are advertisements, never proof that escrow has been deposited.
Missing AI/US/payment authorization blocks external execution or submissions.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

MAX_AGE_HOURS = 24

@dataclass(frozen=True)
class Verdict:
    tier: str
    status: str
    actionable: bool
    reasons: tuple[str, ...]
    score: int
    verified_escrow: bool

    def to_dict(self): return asdict(self)

def _github_issue(value: str):
    from re import fullmatch
    if not isinstance(value, str): return False
    p=urlsplit(value)
    return p.scheme=='https' and p.hostname=='github.com' and not p.username and bool(fullmatch(r'/[^/]+/[^/]+/issues/\d+',p.path)) and not p.query and not p.fragment

def grade(entry: dict, *, now: datetime | None = None) -> Verdict:
    now=now or datetime.now(timezone.utc)
    if not isinstance(entry,dict):
        return Verdict('C','rejected',False,('Malformed record',),0,False)
    reasons=[]
    gh=str(entry.get('issue_url') or '')
    platform=str(entry.get('platform_url') or '')
    p=urlsplit(platform)
    if not _github_issue(gh): reasons.append('No canonical GitHub issue URL')
    if p.scheme!='https' or p.hostname not in {'algora.io','app.opire.dev'}:
        reasons.append('No supported original platform record')
    if entry.get('github_state')!='open': reasons.append('Original issue is closed or unverified')
    if entry.get('reward_status')!='available': reasons.append('Reward not independently shown available')
    amount=entry.get('reward_usd')
    if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not (1<=amount<=100000):
        reasons.append('Reward invalid or missing'); amount=0
    if entry.get('currency')!='USD': reasons.append('Reward currency unverified')
    if entry.get('already_awarded') is not False: reasons.append('Reward payment/completion not ruled out')
    creator=entry.get('creator_identified') is True
    if not creator: reasons.append('Identifiable current payer not confirmed')
    # No current source adapter independently attests deposited escrow.
    # A user-supplied URL or boolean must NEVER assert tier A.
    escrow=False
    current_offer=(creator and entry.get('reward_status')=='available' and
                   entry.get('github_state')=='open' and amount>0 and p.scheme=='https' and
                   p.hostname in {'algora.io','app.opire.dev'} and entry.get('currency')=='USD' and
                   entry.get('already_awarded') is False)
    tier='A' if current_offer and escrow else ('B' if current_offer else 'C')
    if not escrow: reasons.append('No independently verified escrow or binding funding')
    if entry.get('ai_assistance_permitted') is not True: reasons.append('AI-assisted work not explicitly permitted')
    if entry.get('united_states_eligible') is not True: reasons.append('United States eligibility not verified')
    if entry.get('no_deposit_or_fee') is not True: reasons.append('No-upfront-fee participation not verified')
    if entry.get('payment_conditions_documented') is not True: reasons.append('Payment conditions not sufficiently documented')
    if entry.get('acceptance_criteria_clear') is not True: reasons.append('Acceptance requirements unclear')
    if 'python' not in {str(x).lower() for x in entry.get('languages',[]) if isinstance(x,str)}:
        reasons.append('Python capability match not established')
    if entry.get('unresolved_claims') is not False: reasons.append('Prior submissions/claims require review')
    if entry.get('repo_safe_to_run') is not True: reasons.append('Execution safety not admitted')
    observed=entry.get('checked_at')
    try:
        parsed=datetime.fromisoformat(observed.replace('Z','+00:00'))
        if parsed.tzinfo is None: raise ValueError()
        age=(now-parsed).total_seconds()/3600
        if age<0 or age>MAX_AGE_HOURS: reasons.append('Source evidence expired or dated in the future')
    except (TypeError,AttributeError,ValueError): reasons.append('No valid verification timestamp')
    actionable=bool(escrow and tier!='C' and all(x not in reasons for x in (
        'Original issue is closed or unverified','Reward not independently shown available','No supported original platform record')) and
        not any(x in reasons for x in (
            'AI-assisted work not explicitly permitted','United States eligibility not verified',
            'No-upfront-fee participation not verified','Payment conditions not sufficiently documented',
            'Acceptance requirements unclear','Python capability match not established',
            'Prior submissions/claims require review','Execution safety not admitted',
            'Source evidence expired or dated in the future','No valid verification timestamp')))
    # Regardless of funding tier, outside work remains owner-gated.
    return Verdict(tier,'eligible_review' if actionable else 'rejected',actionable,tuple(reasons),
                   max(0, 100-7*len(reasons)),escrow)

def shortlist(entries: list[dict], *, now: datetime | None = None) -> list[dict]:
    """Deduplicate by canonical issue URL; fail closed on conflicting record claims."""
    grouped={}
    for entry in entries:
        if not isinstance(entry,dict): continue
        key=str(entry.get('issue_url') or '').rstrip('/').lower()
        if not key: continue
        grouped.setdefault(key,[]).append(entry)
    result=[]
    for issue, records in grouped.items():
        if len(records)>1:
            result.append({'issue_url':issue,'status':'conflicting_sources','tier':'C',
                           'actionable':False,'score':0,'reasons':['Duplicate platform claims require reconciliation']})
            continue
        verdict=grade(records[0],now=now).to_dict()
        result.append({'issue_url':issue,**verdict})
    return sorted(result,key=lambda r:(not r['actionable'],-r['score'],r['issue_url']))
