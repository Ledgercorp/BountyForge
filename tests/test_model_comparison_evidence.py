import unittest
import json
from pathlib import Path
from bountyforge.model_comparison_evidence import usage,load_record,summarize
from bountyforge.repair_engines import receipt_hash


class EvidenceAccountingTests(unittest.TestCase):
    def test_pre_dispatch_failure_is_zero_requests_and_missing_usage_is_unknown(self):
        self.assertEqual(usage([{'metadata':{'completion_requests':0}}])['completion_requests'],0)
        actual=usage([{'metadata':{'completion_requests':1,'prompt_tokens':100,'completion_tokens':40}}])
        self.assertEqual(actual,{'completion_requests':1,'prompt_tokens':100,'completion_tokens':40})
        self.assertIsNone(usage([{'metadata':{'completion_requests':1}}])['completion_tokens'])
        self.assertIsNone(usage([],unknown=True)['completion_requests'])

    def test_tampered_or_unbound_record_never_becomes_a_score(self):
        with self.assertRaises(ValueError):load_record(b'{}','0'*64)

    def test_actual_v1_timeout_is_blocked_not_three_incorrect_repairs(self):
        record=json.loads((Path(__file__).resolve().parents[1]/'evidence/phase15/comparison_40007714754.json').read_bytes())
        summary=summarize(record);larger=summary['models'][1]
        self.assertEqual(larger['tasks_prepared'],1);self.assertEqual(larger['tasks_completed'],0)
        self.assertEqual(larger['tasks_blocked'],1);self.assertEqual(larger['tasks_not_prepared'],2)
        self.assertIsNone(larger['repair_usage']['completion_tokens'])

    def test_rehashed_receipt_with_substituted_model_authorship_is_rejected(self):
        record=json.loads((Path(__file__).resolve().parents[1]/'evidence/phase15/comparison_40007714754.json').read_bytes())
        attempt=record['models'][0]['jobs'][0]['result']['receipt']['attempts'][0]
        attempt['generation']['raw_response_sha256']='0'*64;attempt['receipt_sha256']=receipt_hash(attempt)
        with self.assertRaisesRegex(ValueError,'AUTONOMOUS_GENERATION_BINDING_REJECTED'):summarize(record)
