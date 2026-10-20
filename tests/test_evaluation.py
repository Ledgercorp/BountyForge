import unittest
from bountyforge.evaluation import evaluate
class EvaluationTests(unittest.TestCase):
 def setUp(self):
  self.c={'issue_url':'https://github.com/a/b/issues/3','platform_url':'https://app.opire.dev/issues/abc','platform_status':'available','github_open':True,'reward_usd':50,'languages':['Python'],'ai_policy':'permitted','us_eligibility':True,'no_payment_required':True,'acceptance_criteria':'unit test','already_solved':False}
 def test_reviewable_not_funding_verified(self):
  d=evaluate(self.c);self.assertEqual(d.state,'review_candidate');self.assertFalse(d.funding_verified);self.assertFalse(d.eligible_for_execution)
 def test_rejects_unknown_ai_rules(self):
  self.c['ai_policy']='unknown';self.assertEqual(evaluate(self.c).state,'rejected')
 def test_rejects_fake_reward(self):
  self.c['reward_usd']='$5000';self.assertEqual(evaluate(self.c).state,'rejected')
 def test_rejects_paid_deposit(self):
  self.c['requirements']='Deposit $15';self.assertEqual(evaluate(self.c).state,'rejected')
 def test_rejects_no_us_proof(self):
  del self.c['us_eligibility'];self.assertEqual(evaluate(self.c).state,'rejected')
if __name__=='__main__':unittest.main()