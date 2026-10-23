import unittest
from bountyforge.model_comparison_evidence import usage,load_record


class EvidenceAccountingTests(unittest.TestCase):
    def test_pre_dispatch_failure_is_zero_requests_and_missing_usage_is_unknown(self):
        self.assertEqual(usage([{'metadata':{'completion_requests':0}}])['completion_requests'],0)
        actual=usage([{'metadata':{'completion_requests':1,'prompt_tokens':100,'completion_tokens':40}}])
        self.assertEqual(actual,{'completion_requests':1,'prompt_tokens':100,'completion_tokens':40})
        self.assertIsNone(usage([{'metadata':{'completion_requests':1}}])['completion_tokens'])
        self.assertIsNone(usage([],unknown=True)['completion_requests'])

    def test_tampered_or_unbound_record_never_becomes_a_score(self):
        with self.assertRaises(ValueError):load_record(b'{}','0'*64)
