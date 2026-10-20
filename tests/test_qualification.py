import unittest
from bountyforge.qualification import qualify
class QualificationTests(unittest.TestCase):
 def test_missing_evidence_blocks(self):
  x=qualify({'tier':'B','language':'python'});self.assertEqual(x.status,'blocked');self.assertFalse(x.can_submit)
 def test_paid_amount_does_not_override_safety(self):
  x=qualify({'tier':'A','reward_usd':500000,'language':'python'})
  self.assertFalse(x.external_execution_authorized)
 def test_good_facts_do_not_authorize_submission(self):
  c={'tier':'B','github_state':'open','platform_availability':'current','award_already_paid':False,
     'ai_allowed':True,'us_eligible':True,'payment_conditions_known':True,'upfront_payment_required':False,
     'language':'python','narrow_tests':True,'third_party_code_sandbox_certified':True}
  b={'complete':True,'attempted':5,'passed':4,'full_upstream_suites':1}
  x=qualify(c,b);self.assertEqual(x.status,'candidate_for_manual_review');self.assertFalse(x.can_submit)
 def test_skipped_full_suite_blocks(self):
  c={'tier':'B','github_state':'open','platform_availability':'current','award_already_paid':False,
     'ai_allowed':True,'us_eligible':True,'payment_conditions_known':True,'upfront_payment_required':False,
     'language':'python','narrow_tests':True,'third_party_code_sandbox_certified':True}
  b={'complete':True,'attempted':5,'passed':4,'full_upstream_suites':0}
  self.assertIn('Full upstream compatibility unverified',qualify(c,b).reasons)
if __name__=='__main__':unittest.main()