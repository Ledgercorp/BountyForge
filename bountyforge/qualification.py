"""Risk-gated commercial queue: no money or safety claims based on model judgment."""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class Qualification:
    status: str
    reasons: tuple[str,...]
    priority: int
    funding_tier: str
    external_execution_authorized: bool = False
    can_submit: bool = False

    def to_dict(self): return asdict(self)


def qualify(candidate:dict, benchmark:dict|None=None) -> Qualification:
    """Never equate a current advert with verified escrow or automatic payment.

    This gate is intentionally stricter than discovery, which is read-only.
    """
    if not isinstance(candidate,dict):
        return Qualification('rejected',('Malformed candidate',),0,'C')
    reasons=[]
    # No current source adapter independently attests escrow or binding funding.
    # Candidate-controlled booleans, reward amounts and tiers cannot supply that
    # missing evidence. Keep the offer available for research, never execution.
    reasons.append('Funding has no independently verified escrow or binding commitment')
    tier=candidate.get('tier','C')
    if tier not in {'A','B'}:
        reasons.append('No independently supported current monetary offer')
        tier='C'
    if candidate.get('github_state')!='open':reasons.append('Original GitHub issue not independently open')
    if candidate.get('platform_availability')!='current':reasons.append('Platform reward availability unverified')
    if candidate.get('award_already_paid') is not False:reasons.append('Prior payment/claim unresolved')
    if candidate.get('ai_allowed') is not True:reasons.append('AI assistance permission unverified')
    if candidate.get('us_eligible') is not True:reasons.append('US participation eligibility unverified')
    if candidate.get('payment_conditions_known') is not True:reasons.append('Payout terms unresolved')
    if candidate.get('upfront_payment_required') is not False:reasons.append('No-fee participation unverified')
    if candidate.get('language')!='python':reasons.append('Outside verified Python capability')
    if candidate.get('narrow_tests') is not True:reasons.append('No bounded reproducible target tests')
    if candidate.get('third_party_code_sandbox_certified') is not True:
        reasons.append('Arbitrary third-party repository execution not safely admitted')
    # Even a successful excerpt benchmark is NOT proof of full-repo reliability.
    if not isinstance(benchmark,dict) or benchmark.get('complete') is not True:
        reasons.append('Five-issue comparable benchmark incomplete')
    else:
        tries=benchmark.get('attempted',0);success=benchmark.get('passed',0)
        if not isinstance(tries,int) or not isinstance(success,int) or tries < 5 or success < 2:
            reasons.append('Model excerpt reliability below measured entry threshold')
        if benchmark.get('full_upstream_suites',0)<1:
            reasons.append('Full upstream compatibility unverified')
    status='candidate_for_manual_review' if not reasons else 'blocked'
    return Qualification(status,tuple(reasons),max(0,100-10*len(reasons)),tier)
