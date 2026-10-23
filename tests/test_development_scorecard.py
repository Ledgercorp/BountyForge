import json
from pathlib import Path
import unittest
from bountyforge.development_scorecard import measure
from bountyforge.repair_engines import receipt_hash


class ScorecardTests(unittest.TestCase):
    def record(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'evidence/phase14/codex_session.json').read_bytes())
        for call in data['calls']:
            if call['tool']=='submit_owned_repair':
                record=json.loads(call['response']['result']['content'][0]['text'])
                if record.get('case_id')=='invoice-summary':return record

    def test_actual_receipt_reports_unknown_codex_usage_as_null(self):
        result=measure('invoice-summary','CODEX_AGENT',[self.record()])
        self.assertTrue(result['verified_repair']);self.assertEqual(result['valid_patches'],1)
        self.assertEqual(result['targeted_test_methods_in_passing_suites'],8)
        self.assertIsNone(result['model_calls']);self.assertIsNone(result['prompt_tokens'])
        self.assertFalse(result['independent_evaluation'])

    def test_rehashed_but_contradictory_receipt_cannot_become_a_success_metric(self):
        record=self.record();record['targeted']['passed']=False
        record['receipt_sha256']=receipt_hash(record)
        with self.assertRaises(ValueError):measure('invoice-summary','CODEX_AGENT',[record])
