from datetime import datetime, timezone
import unittest
from bountyforge.opportunities import grade, shortlist
NOW=datetime(2026,10,20,12,30,tzinfo=timezone.utc)

class OpportunityTests(unittest.TestCase):
    def candidate(self):
        return dict(issue_url='https://github.com/owner/repo/issues/23',
            platform_url='https://algora.io/owner/bounties?status=open',github_state='open',
            reward_status='available',reward_usd=50,currency='USD',already_awarded=False,
            creator_identified=True,escrow_verified=False,
            ai_assistance_permitted=True,united_states_eligible=True,no_deposit_or_fee=True,
            payment_conditions_documented=True,acceptance_criteria_clear=True,
            languages=['Python'],unresolved_claims=False,repo_safe_to_run=True,
            checked_at='2026-10-20T12:00:00Z')
    def test_identifiable_open_reward_is_tier_b_not_escrow(self):
        r=grade(self.candidate(),now=NOW)
        self.assertEqual(r.tier,'B')
        self.assertFalse(r.verified_escrow)
        self.assertFalse(r.actionable)
    def test_closure_beats_platform_claim(self):
        x=self.candidate();x['github_state']='closed'
        r=grade(x,now=NOW)
        self.assertEqual(r.tier,'C');self.assertFalse(r.actionable)
    def test_missing_us_permission_blocks(self):
        x=self.candidate();x['united_states_eligible']=None
        self.assertFalse(grade(x,now=NOW).actionable)
    def test_missing_ai_policy_blocks(self):
        x=self.candidate();x['ai_assistance_permitted']=None
        self.assertFalse(grade(x,now=NOW).actionable)
    def test_false_escrow_claim_not_tier_a(self):
        x=self.candidate();x['escrow_verified']=True
        self.assertEqual(grade(x,now=NOW).tier,'B')
    def test_user_supplied_escrow_receipt_never_establishes_tier_a(self):
        x=self.candidate();x.update(escrow_verified=True,escrow_evidence_url='https://example.org/receipt',release_conditions_documented=True)
        self.assertEqual(grade(x,now=NOW).tier,'B')
    def test_stale_blocks(self):
        x=self.candidate();x['checked_at']='2026-10-17T12:00:00Z'
        self.assertFalse(grade(x,now=NOW).actionable)
    def test_duplicate_fails_closed(self):
        records=[self.candidate(),self.candidate()]
        xs=shortlist(records,now=NOW)
        self.assertEqual(xs[0]['tier'],'C');self.assertFalse(xs[0]['actionable'])
    def test_no_deposit_unknown_blocks(self):
        x=self.candidate();x['no_deposit_or_fee']=None
        self.assertFalse(grade(x,now=NOW).actionable)
    def test_reward_missing_blocks(self):
        x=self.candidate();x['reward_usd']=0
        self.assertEqual(grade(x,now=NOW).tier,'C')
    def test_repo_safety_blocks(self):
        x=self.candidate();x['repo_safe_to_run']=False
        self.assertFalse(grade(x,now=NOW).actionable)
    def test_nonpython_blocks(self):
        x=self.candidate();x['languages']=['Go']
        self.assertFalse(grade(x,now=NOW).actionable)

if __name__=='__main__':unittest.main()
