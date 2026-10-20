"""Deterministic preflight ranking; platform claims are never funding proof."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from urllib.parse import urlsplit

ACCEPTED_LANGUAGES = frozenset({'python'})
REJECT_TERMS = ('deposit','membership fee','paid api','paid subscription','required gpu','captcha bypass','credential harvesting')

@dataclass(frozen=True)
class Decision:
    state: str
    score: int
    reasons: tuple[str, ...]
    eligible_for_execution: bool
    funding_verified: bool

    def to_dict(self) -> dict: return asdict(self)

def evaluate(candidate: dict) -> Decision:
    """Unknown funding or eligibility always blocks external work."""
    reasons = []
    if not isinstance(candidate, dict):
        return Decision('rejected',0,('Malformed candidate',),False,False)
    url = str(candidate.get('issue_url') or candidate.get('url') or '')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'github.com' or '/issues/' not in parsed.path:
        reasons.append('Unverified original GitHub issue URL')
    platform_url = str(candidate.get('platform_url') or '')
    verified_source = urlsplit(platform_url)
    original_platform = verified_source.scheme == 'https' and verified_source.netloc in {'algora.io','app.opire.dev'}
    if not original_platform:
        reasons.append('No original platform listing')
    # Platform status is an advertisement, not money held in escrow.
    if candidate.get('platform_status') != 'available':
        reasons.append('Platform does not confirm available reward')
    if candidate.get('github_open') is not True:
        reasons.append('GitHub issue closure/availability unverified')
    reward = candidate.get('reward_usd')
    if isinstance(reward,bool) or not isinstance(reward,(int,float)) or not 1 <= reward <= 100_000:
        reasons.append('No credible numeric reward')
        reward = 0
    langs = {str(x).lower() for x in candidate.get('languages',[]) if isinstance(x,str)}
    if not langs.intersection(ACCEPTED_LANGUAGES):
        reasons.append('Python not listed as an implementation language')
    text = (str(candidate.get('title',''))+' '+str(candidate.get('requirements',''))).lower()
    if any(x in text for x in REJECT_TERMS):
        reasons.append('High-risk or paid-resource dependency')
    if candidate.get('ai_policy') not in ('permitted','documented_permission'):
        reasons.append('AI assistance permission unverified')
    if candidate.get('us_eligibility') is not True:
        reasons.append('US eligibility unverified')
    if candidate.get('no_payment_required') is not True:
        reasons.append('Zero-cost participation unverified')
    if not candidate.get('acceptance_criteria'):
        reasons.append('Missing acceptance criteria')
    if candidate.get('already_solved') is not False:
        reasons.append('Competition/completion status unverified')
    score = max(0, 100 - 11 * len(reasons) - (30 if reward > 500 else 0))
    passed = not reasons
    return Decision('review_candidate' if passed else 'rejected',score,tuple(reasons),False,False)