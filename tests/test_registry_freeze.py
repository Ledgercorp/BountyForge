import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.verify_historical_registry import verify,ROOT
from bountyforge.repair_engines import receipt_hash


class RegistryFreezeTests(unittest.TestCase):
    def test_frozen_registry_is_metadata_preparation_not_measured_accuracy(self):
        r=verify();self.assertEqual(r['tasks'],30);self.assertEqual(r['repositories'],6)
        self.assertFalse(r['execution_admitted']);self.assertIsNone(r['unseen_accuracy'])

    def test_changed_identity_or_promoted_admission_is_rejected(self):
        for promote in (False,True):
            with self.subTest(promote=promote),tempfile.TemporaryDirectory() as t:
                root=Path(t);contract=json.loads((ROOT/'evidence/phase23-25/evaluation-contract.json').read_text())
                for name in contract['frozen_files']:
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
                registry=json.loads((ROOT/'evidence/phase23-25/historical-registry.json').read_text())
                if promote:registry['independently_unseen']=True
                else:registry['tasks'][0]['expected_failing_tests'].append('FAKE_TEST')
                registry['receipt_sha256']=receipt_hash(registry)
                raw=(json.dumps(registry,indent=2,sort_keys=True)+'\n').encode()
                # Even a newly hashed snapshot cannot invent blindness or valid test IDs.
                contract['historical_registry_sha256']=hashlib.sha256(raw).hexdigest()
                dest=root/'evidence/phase23-25';dest.mkdir(parents=True)
                (dest/'historical-registry.json').write_bytes(raw)
                (dest/'evaluation-contract.json').write_text(json.dumps(contract))
                with self.assertRaises(ValueError):verify(root)
