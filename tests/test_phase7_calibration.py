import unittest
from bountyforge.phase7_calibration import CASES,CalibrationBlocked,manifest,replay_one,replay_catalog

class OwnedCalibrationTests(unittest.TestCase):
    def test_four_new_owned_regression_baselines_and_references(self):
        out=replay_catalog()
        self.assertEqual(out['case_count'],4)
        self.assertEqual(out['baseline_defects_reproduced'],4)
        self.assertEqual(out['owned_reference_fixes_verified'],4)
        self.assertEqual(out['independent_ai_repairs_tested'],0)
        self.assertFalse(out['commercial_repair_accuracy_established'])
    def test_catalog_integrity_is_repeatable(self):
        a=manifest();b=manifest()
        self.assertEqual(a,b)
        self.assertEqual(len(a['manifest_sha256']),64)
        self.assertEqual({c['id'] for c in a['cases']}, {c['id'] for c in CASES})
        self.assertFalse(a['hidden_or_unseen_test_set'])
    def test_untrusted_code_and_tampering_rejected(self):
        for c in CASES:
            with self.subTest(case=c['id']):
                with self.assertRaises(CalibrationBlocked):
                    replay_one(c['id'],c['source'].encode(),c['fixed'].encode()+b'\n')
                with self.assertRaises(CalibrationBlocked):
                    replay_one(c['id'],b'__import__("os").system("id")',c['fixed'].encode())
        with self.assertRaises(CalibrationBlocked):replay_one('external-code',b'',b'')

if __name__=='__main__':unittest.main()
