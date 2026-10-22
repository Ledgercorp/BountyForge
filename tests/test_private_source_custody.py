"""Owned offline fixtures for a non-executable private source custody snapshot."""
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.paid_scope_review import SQLiteScopeReviewStore, PaidScopeReview
from bountyforge.private_source_inventory import PrivateSourceRejected
from bountyforge.private_source_custody import create_review_snapshot, verify_private_snapshot

NOW = 1792616400
KEY = b'unit-private-custody-owner-secret-33'
SESSION = hashlib.sha256(b'unit-private-custody-session').hexdigest()


class PrivateSourceCustodyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.source_root = base / 'private-input'
        self.source_root.mkdir(mode=0o700)
        (self.source_root / 'tests').mkdir(mode=0o700)
        self.source = self.source_root / 'source.py'
        self.test = self.source_root / 'tests' / 'test_regression.py'
        self.source.write_text('def value():\n    return 2\n')
        self.test.write_text('import unittest\nclass Case(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(2, 2)\n')
        self.source.chmod(0o600)
        self.test.chmod(0o600)
        self.vault = base / 'vault'
        self.vault.mkdir(mode=0o700)
        self.payload = {
            'schema': 1, 'session_sha256': SESSION,
            'source_path': 'source.py',
            'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'test_path': 'tests/test_regression.py',
            'tests_sha256': hashlib.sha256(self.test.read_bytes()).hexdigest(),
            'dependency_policy': 'stdlib_only_v1',
            'source_access_receipt_sha256': 'b' * 64,
            'model_sharing_receipt_sha256': 'c' * 64,
            'owner_approval_id': 'd' * 32, 'expires_at': NOW + 600
        }
        signed = {'payload': dict(self.payload), 'signature': hmac.new(
            KEY, json.dumps(self.payload, sort_keys=True,
                            separators=(',', ':')).encode('ascii'),
            hashlib.sha256).hexdigest()}
        payments = SQLitePaidReviewStore(base / 'prior-paid-review.sqlite')
        payments.write({'version': 1, 'orders': [{
            'session_sha256': SESSION, 'state': 'awaiting_owner_scope_review',
            'amount_cents': 4900, 'verified_at': '2026-10-21T21:00:00+00:00'
        }]}, None)
        scope = SQLiteScopeReviewStore(base / 'scope-review.sqlite')
        self.review = PaidScopeReview(scope, payments, approval_key=KEY)
        initial = self.review.record_scope(SESSION, signed, now=NOW)
        self.lease = self.review.claim_review(
            SESSION, expected_fence=initial['fence'], now=NOW, ttl=60)

    def snapshot(self):
        return create_review_snapshot(
            self.source_root, self.vault, self.review, SESSION,
            token=self.lease['token'], expected_fence=self.lease['fence'],
            now=NOW + 2)

    def test_snapshots_are_private_integrity_only_and_independently_reopen(self):
        result = self.snapshot()
        self.assertEqual(result['kind'], 'private_custody_snapshot')
        self.assertEqual(result['source_sha256'], self.payload['source_sha256'])
        self.assertEqual(result['test_sha256'], self.payload['tests_sha256'])
        for key in ('execution_authorized', 'source_accepted', 'delivery_authorized',
                    'model_sharing_verified', 'fresh_payment_verified', 'private_worker_admitted'):
            self.assertIs(result[key], False)
        self.assertNotIn(self.lease['token'], str(result))
        self.assertNotIn('return 2', str(result))
        snapshot = self.vault / result['snapshot_name']
        self.assertTrue(snapshot.is_dir())
        self.assertEqual(snapshot.stat().st_mode & 0o777, 0o700)
        self.assertEqual((snapshot / 'source.py').read_bytes(), self.source.read_bytes())
        self.assertEqual((snapshot / 'tests/test_regression.py').read_bytes(), self.test.read_bytes())
        independently = verify_private_snapshot(snapshot, self.payload)
        self.assertEqual(independently['snapshot_sha256'], result['snapshot_sha256'])
        self.assertEqual(independently['source_sha256'], self.payload['source_sha256'])
        self.assertFalse(independently['execution_authorized'])
        self.assertNotIn('return 2', str(independently))

    def test_original_changes_after_snapshot_do_not_change_verifiable_copy(self):
        result = self.snapshot()
        self.source.write_text('def value():\n    return 99\n')
        self.source.chmod(0o600)
        self.assertTrue(verify_private_snapshot(
            self.vault / result['snapshot_name'], self.payload)['hashes_verified'])
        with self.assertRaises(PrivateSourceRejected):
            self.snapshot()

    def test_snapshot_tamper_and_added_files_fail_read_only_reverification(self):
        result = self.snapshot()
        snapshot = self.vault / result['snapshot_name']
        source = snapshot / 'source.py'
        source.write_text('def value():\n    return 999\n')
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, self.payload)
        source.write_bytes(self.source.read_bytes())
        snapshot.joinpath('.credentials').write_text('secret')
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, self.payload)

    def test_symlink_and_hardlink_tampering_rejected(self):
        result = self.snapshot()
        snapshot = self.vault / result['snapshot_name']
        target = snapshot / 'source.py'
        external = self.vault / 'external.py'
        external.write_bytes(target.read_bytes())
        external.chmod(0o600)
        target.unlink()
        target.symlink_to(external)
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, self.payload)
        target.unlink()
        os.link(external, target)
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, self.payload)

    def test_missing_custody_receipt_and_wrong_scope_rejected(self):
        result = self.snapshot()
        snapshot = self.vault / result['snapshot_name']
        bad = dict(self.payload, tests_sha256='f' * 64)
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, bad)
        (snapshot / 'snapshot.json').unlink()
        with self.assertRaises(PrivateSourceRejected):
            verify_private_snapshot(snapshot, self.payload)

    def test_expired_or_revoked_review_cannot_create_snapshot(self):
        self.review.hold(SESSION, reason='owner_revoked', now=NOW + 1)
        with self.assertRaises(PrivateSourceRejected):
            self.snapshot()
        self.assertEqual(list(self.vault.iterdir()), [])

    def test_concurrent_review_revocation_cannot_finalize_snapshot(self):
        import bountyforge.private_source_custody as custody
        real_write = custody._write_snapshot
        def revoke_after_write(*args, **kwargs):
            value = real_write(*args, **kwargs)
            self.review.hold(SESSION, reason='owner_revoked', now=NOW + 1)
            return value
        with patch('bountyforge.private_source_custody._write_snapshot', side_effect=revoke_after_write):
            with self.assertRaises(PrivateSourceRejected):
                self.snapshot()
        self.assertFalse(any(p.name.startswith('sealed-') for p in self.vault.iterdir()))

    def test_vault_with_existing_source_or_symlink_not_allowed(self):
        with self.assertRaises(PrivateSourceRejected):
            create_review_snapshot(self.source_root, self.source_root, self.review, SESSION,
                token=self.lease['token'], expected_fence=self.lease['fence'], now=NOW+2)
        link = Path(self.vault.parent) / 'linked-vault'
        link.symlink_to(self.vault, target_is_directory=True)
        with self.assertRaises(PrivateSourceRejected):
            create_review_snapshot(self.source_root, link, self.review, SESSION,
                token=self.lease['token'], expected_fence=self.lease['fence'], now=NOW+2)


if __name__ == '__main__':
    unittest.main()
