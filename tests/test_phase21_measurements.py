import copy
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch


class QualityEvidenceTests(unittest.TestCase):
    def module(self):
        try:import phase21_measurements
        except ImportError:self.fail('Cross-checked repair evidence accounting is missing')
        return phase21_measurements

    def historical_receipt(self):
        path=Path(__file__).resolve().parents[1]/'evidence/phase20/chunk-count-native.json'
        case=json.loads(path.read_text())['cases'][0]
        return case['attempts'][0]['verification']['owned_verifier_receipt']

    def test_claimed_success_cannot_survive_a_failed_or_missing_independent_test(self):
        m=self.module();receipt=self.historical_receipt()
        self.assertTrue(m.verified_receipt(receipt,receipt['source_sha256'],receipt['tests_sha256'],6))
        from bountyforge.repair_engines import receipt_hash
        for change in ('targeted','independent'):
            bad=copy.deepcopy(receipt);bad[change]['passed']=False;bad['receipt_sha256']=receipt_hash(bad)
            with self.assertRaises(ValueError):m.verified_receipt(bad,receipt['source_sha256'],receipt['tests_sha256'],6)
        bad=copy.deepcopy(receipt);bad.pop('independent');bad['receipt_sha256']=receipt_hash(bad)
        with self.assertRaises(ValueError):m.verified_receipt(bad,receipt['source_sha256'],receipt['tests_sha256'],6)

    def test_source_identity_and_receipt_tampering_do_not_become_accuracy_measurements(self):
        m=self.module();receipt=self.historical_receipt()
        with self.assertRaises(ValueError):m.verified_receipt(receipt,'0'*64,receipt['tests_sha256'],6)
        receipt['outcome']='TEST_FAILED'
        with self.assertRaises(ValueError):m.verified_receipt(receipt,receipt['source_sha256'],receipt['tests_sha256'],6)

    def test_first_attempt_and_retry_success_remain_distinct_cases(self):
        m=self.module()
        rows=[{'verified':True,'first_attempt_verified':True,'retry_assisted':False},
              {'verified':True,'first_attempt_verified':False,'retry_assisted':True},
              {'verified':False,'first_attempt_verified':False,'retry_assisted':False}]
        self.assertEqual(m.success_counts(rows),{'verified_repairs':2,'first_attempt_successes':1,'retry_assisted_successes':1})

    def test_missing_results_are_explicitly_unmeasured_not_a_zero_accuracy_score(self):
        m=self.module();manifest=Path(__file__).resolve().parents[1]/'fixtures/phase21/manifest.json'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'fixtures/phase21/manifest.json';target.parent.mkdir(parents=True)
            target.write_bytes(manifest.read_bytes())
            with patch('phase21_measurements.ROOT',root):result=m.build()
            self.assertEqual(result.get('measurement_status'),'UNMEASURED')
            self.assertTrue(all(v['recorded_tasks']==0 for v in result['arms'].values()))
