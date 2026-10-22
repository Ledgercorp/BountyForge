"""Review-lease integration uses only fake payment proof and owned private bytes."""
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import bountyforge.private_source_inventory as inventory

from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.paid_scope_review import SQLiteScopeReviewStore, PaidScopeReview
from bountyforge.private_source_inventory import (
    inspect_recorded_private_scope, PrivateSourceRejected,
)

NOW = 1792616400
KEY = b'owner-unit-approval-key-thirtytwo!!!'
SESSION = hashlib.sha256(b'fake-session-for-review-only').hexdigest()


class PrivateReviewLeaseBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        container = Path(self.temp.name)
        self.source_root = container / 'private-source'
        self.source_root.mkdir(mode=0o700)
        (self.source_root / 'tests').mkdir(mode=0o700)
        self.source = self.source_root / 'module.py'
        self.tests = self.source_root / 'tests/test_regression.py'
        self.source.write_text('def identity(value):\n    return value\n')
        self.tests.write_text('import unittest\n\nclass Check(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1, 1)\n')
        self.source.chmod(0o600)
        self.tests.chmod(0o600)
        self.payload = {
            'schema': 1, 'session_sha256': SESSION,
            'source_path': 'module.py',
            'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'test_path': 'tests/test_regression.py',
            'tests_sha256': hashlib.sha256(self.tests.read_bytes()).hexdigest(),
            'dependency_policy': 'stdlib_only_v1',
            'source_access_receipt_sha256': 'b' * 64,
            'model_sharing_receipt_sha256': 'c' * 64,
            'owner_approval_id': 'd' * 32,
            'expires_at': NOW + 600
        }
        approval = {'payload': dict(self.payload),
                    'signature': hmac.new(KEY,
                        json.dumps(self.payload, sort_keys=True,
                                   separators=(',', ':')).encode('ascii'),
                        hashlib.sha256).hexdigest()}
        self.reviews = SQLitePaidReviewStore(container / 'paid.sqlite3')
        self.reviews.write({'version': 1, 'orders': [{
            'session_sha256': SESSION, 'state': 'awaiting_owner_scope_review',
            'amount_cents': 4900, 'verified_at': '2026-10-21T21:00:00+00:00'
        }]}, None)
        self.scope_store = SQLiteScopeReviewStore(container / 'scope.sqlite3')
        self.journal = PaidScopeReview(self.scope_store, self.reviews, approval_key=KEY)
        created = self.journal.record_scope(SESSION, approval, now=NOW)
        self.claim = self.journal.claim_review(SESSION, expected_fence=created['fence'],
                                               now=NOW, ttl=60)

    def inspect(self, **updates):
        return inspect_recorded_private_scope(
            self.source_root, self.journal, SESSION,
            token=self.claim['token'], expected_fence=self.claim['fence'],
            now=NOW + 2, **updates
        )

    def test_signed_stored_lease_binds_to_exact_private_bytes_without_authority(self):
        evidence = self.inspect()
        self.assertEqual(evidence['kind'], 'private_source_digest_inspection')
        self.assertEqual(evidence['session_sha256'], SESSION)
        self.assertEqual(evidence['lease_fence'], self.claim['fence'])
        self.assertTrue(evidence['signed_scope_matched'])
        self.assertTrue(evidence['prior_payment_review_present'])
        self.assertTrue(evidence['review_lease_validated'])
        self.assertFalse(evidence['fresh_payment_verified'])
        for field in ('execution_authorized', 'source_accepted', 'delivery_authorized'):
            self.assertIs(evidence[field], False)
        self.assertNotIn(self.claim['token'], str(evidence))

    def test_released_or_revoked_review_lease_blocks_byte_inspection(self):
        self.journal.hold(SESSION, reason='owner_revoked', now=NOW + 1)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_expired_token_and_wrong_fence_block_before_file_access(self):
        with self.assertRaises(PrivateSourceRejected):
            inspect_recorded_private_scope(
                self.source_root, self.journal, SESSION,
                token=self.claim['token'], expected_fence=self.claim['fence'],
                now=NOW + 61)
        with self.assertRaises(PrivateSourceRejected):
            inspect_recorded_private_scope(
                self.source_root, self.journal, SESSION,
                token=self.claim['token'], expected_fence=self.claim['fence'] - 1,
                now=NOW + 2)

    def test_modified_private_source_fails_even_with_signed_scope(self):
        self.source.write_text('def identity(value):\n    return None\n')
        self.source.chmod(0o600)
        with self.assertRaises(PrivateSourceRejected):
            self.inspect()

    def test_other_verifier_key_cannot_inspect_approved_source(self):
        impostor = PaidScopeReview(self.scope_store, self.reviews,
                                   approval_key=b'impostor-owner-scope-key-32bytes!!!!')
        with self.assertRaises(PrivateSourceRejected):
            inspect_recorded_private_scope(
                self.source_root, impostor, SESSION,
                token=self.claim['token'], expected_fence=self.claim['fence'], now=NOW + 2)

    def test_concurrent_revocation_during_byte_scan_fails_closed(self):
        real_inspect = inventory.inspect_private_source
        def revoke_after_read(root, payload):
            evidence = real_inspect(root, payload)
            self.journal.hold(SESSION, reason='owner_revoked', now=NOW + 1)
            return evidence
        with patch('bountyforge.private_source_inventory.inspect_private_source',
                   side_effect=revoke_after_read):
            with self.assertRaises(PrivateSourceRejected):
                self.inspect()
        self.assertEqual(self.scope_store.read()[0]['plans'][0]['state'], 'blocked')

    def test_claim_cannot_be_pretended_from_plain_dict(self):
        with self.assertRaises(PrivateSourceRejected):
            inspect_recorded_private_scope(
                self.source_root, {'paid': True}, SESSION,
                token=self.claim['token'], expected_fence=self.claim['fence'], now=NOW + 2)


if __name__ == '__main__':
    unittest.main()
