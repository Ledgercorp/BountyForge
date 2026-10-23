import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.phase7_owned_demo import (OwnedOnlyLedger,SyntheticBlocked,
 SOURCE,PATCHED,replay,owned_demo,SOURCE_HASH,PATCHED_HASH,package_record,canonical,digest)

JOB='synthetic_0123456789abcdef'
class OwnedFulfillmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.pack=self.root/'review';self.pack.mkdir(mode=0o700)
        self.ledger=OwnedOnlyLedger(self.root/'ledger.sqlite');self.addCleanup(self.ledger.close)
    def test_end_to_end_inert_review_receipt(self):
        proof=owned_demo(self.ledger,self.pack)
        self.assertEqual(proof['state'],'AWAITING_OWNER_APPROVAL')
        self.assertEqual(proof['revision'],4)
        self.assertFalse(proof['delivery_authorized'])
        self.assertFalse(proof['real_payment_verified'])
        file=self.pack/(JOB+'.review.json')
        self.assertEqual(digest(file.read_bytes()),proof['package_sha256'])
        self.assertFalse(json.loads(file.read_bytes())['customer_rights_verified'])
    def test_duplicate_job_and_stale_lease(self):
        self.assertTrue(self.ledger.create(JOB));self.assertFalse(self.ledger.create(JOB))
        scope={'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False}
        self.ledger.advance(JOB,0,'SCOPE_REVIEWED',scope)
        with self.assertRaises(SyntheticBlocked):self.ledger.advance(JOB,0,'SCOPE_REVIEWED',scope)
    def test_wrong_payment_and_consent_blocked(self):
        self.ledger.create(JOB)
        with self.assertRaises(SyntheticBlocked):
            self.ledger.advance(JOB,0,'SCOPE_REVIEWED',
              {'kind':'owned_scope','real_payment_verified':True,'customer_rights_verified':True})
        self.assertEqual(self.ledger.read(JOB)['step'],'CREATED')
    def test_never_executes_unapproved_code(self):
        for candidate in (PATCHED+b'\n',b'__import__("os").system("id")'):
            with self.assertRaises(SyntheticBlocked):replay(SOURCE,candidate)
        self.assertTrue(replay(SOURCE,PATCHED)['repair_passed'])
    def test_early_verification_and_unsealed_package_refused(self):
        self.ledger.create(JOB)
        with self.assertRaises(SyntheticBlocked):
            self.ledger.advance(JOB,0,'VERIFIED',replay(SOURCE,PATCHED))
        scope={'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False}
        self.ledger.advance(JOB,0,'SCOPE_REVIEWED',scope)
        self.ledger.advance(JOB,1,'PROPOSED',{'kind':'owned_patch','patch_sha256':PATCHED_HASH})
        self.ledger.advance(JOB,2,'VERIFIED',replay(SOURCE,PATCHED))
        with self.assertRaises(SyntheticBlocked):
            self.ledger.advance(JOB,3,'AWAITING_OWNER_APPROVAL',
                {'kind':'owned_package','package_sha256':digest(canonical(package_record(JOB))+b'\n'),
                 'delivery_authorized':False})
    def test_cannot_reuse_revoked_job(self):
        self.ledger.create(JOB)
        self.ledger.advance(JOB,0,'HELD',{'kind':'owned_hold','delivery_authorized':False})
        with self.assertRaises(SyntheticBlocked):owned_demo(self.ledger,self.pack)
    def test_cas_survives_second_sqlite_connection(self):
        self.ledger.create(JOB)
        second=OwnedOnlyLedger(self.root/'ledger.sqlite')
        try:
            self.assertEqual(second.read(JOB)['rev'],0)
            second.advance(JOB,0,'SCOPE_REVIEWED',
              {'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False})
            with self.assertRaises(SyntheticBlocked):
                self.ledger.advance(JOB,0,'SCOPE_REVIEWED',
                  {'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False})
        finally:second.close()
    def test_private_directory_and_id_enforced(self):
        with self.assertRaises(SyntheticBlocked):self.ledger.create('cs_live_fake')
        self.pack.chmod(0o777)
        try:
            with self.assertRaises(SyntheticBlocked):owned_demo(self.ledger,self.pack)
        finally:self.pack.chmod(0o700)

if __name__=='__main__': unittest.main()
