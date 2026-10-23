"""Owned metadata only: mocked payment history, real private CAS persistence."""
import copy
import hashlib
import hmac
import importlib.util
import json
import tempfile
import unittest
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.paid_review_ledger import ReviewLedgerRejected

spec = importlib.util.find_spec('bountyforge.paid_scope_review')
if spec:
    from bountyforge import paid_scope_review as scope_module
else:
    scope_module = None

NOW = 1792616400
KEY = b'owned-unit-approval-key-32-bytes!!!'
SESSION = hashlib.sha256(b'owned-unit-session').hexdigest()


def approval(**updates):
    payload = {'schema': 1, 'session_sha256': SESSION, 'source_path': 'module.py',
               'source_sha256': 'a' * 64, 'tests_sha256': 'b' * 64,
               'test_path': 'tests/test_regression.py', 'dependency_policy': 'stdlib_only_v1',
               'source_access_receipt_sha256': 'c' * 64,
               'model_sharing_receipt_sha256': 'd' * 64,
               'owner_approval_id': 'e' * 32, 'expires_at': NOW + 3600}
    payload.update(updates)
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return {'payload': payload, 'signature': hmac.new(KEY, encoded, hashlib.sha256).hexdigest()}


class PaidScopeReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(scope_module, 'Metadata-only scope journal is not implemented')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.review = SQLitePaidReviewStore(root / 'paid-review.sqlite3')
        self.review.write({'version': 1, 'orders': [
            {'session_sha256': SESSION, 'state': 'awaiting_owner_scope_review',
             'amount_cents': 4900, 'verified_at': '2026-10-21T21:00:00+00:00'}]}, None)
        self.path = root / 'work-scope.sqlite3'
        self.store = scope_module.SQLiteScopeReviewStore(self.path)
        self.journal = scope_module.PaidScopeReview(self.store, self.review, approval_key=KEY)

    def create(self):
        return self.journal.record_scope(SESSION, approval(), now=NOW)

    def test_owner_scope_is_bound_to_existing_payment_and_persists_idempotently(self):
        first = self.create()
        self.assertEqual(first['state'], 'awaiting_private_execution_admission')
        self.assertFalse(first['execution_authorized'])
        self.assertFalse(first['delivery_authorized'])
        original = self.store.read()
        reopened = scope_module.PaidScopeReview(scope_module.SQLiteScopeReviewStore(self.path),
                                                self.review, approval_key=KEY)
        again = reopened.record_scope(SESSION, approval(), now=NOW + 1)
        self.assertEqual(again['status'], 'already_recorded')
        self.assertEqual(self.store.read(), original)
        state = original[0]
        self.assertEqual(len(state['plans']), 1)
        self.assertNotIn('4900', json.dumps(state))

    def test_customer_flags_cannot_forge_scope_approval_or_change_signed_source(self):
        wrong = approval(); wrong['payload']['source_sha256'] = 'f' * 64
        cases = [wrong, {'owner_approved': True, 'payment_verified': True},
                 approval(source_path='../secrets.py'), approval(source_path='tests/test_x.py'),
                 approval(test_path='custom.sh'), approval(dependency_policy='pip_install'),
                 approval(expires_at=NOW - 1), approval(expires_at=NOW + 32 * 86400),
                 approval(execution_authorized=True)]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ReviewLedgerRejected):
                self.journal.record_scope(SESSION, item, now=NOW)
        self.assertEqual(self.store.read(), (None, None))

    def test_unreviewed_payment_and_conflicting_scope_are_not_admitted(self):
        unknown = 'f' * 64
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.record_scope(unknown, approval(session_sha256=unknown), now=NOW)
        self.create()
        before = self.store.read()
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.record_scope(SESSION, approval(source_sha256='f' * 64), now=NOW)
        self.assertEqual(self.store.read(), before)

    def test_expired_review_lease_recovers_with_fencing_and_no_duplicate_claim(self):
        created = self.create()
        first = self.journal.claim_review(SESSION, expected_fence=created['fence'], now=NOW, ttl=10)
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.claim_review(SESSION, expected_fence=first['fence'], now=NOW + 1, ttl=10)
        reopened = scope_module.PaidScopeReview(scope_module.SQLiteScopeReviewStore(self.path),
                                                self.review, approval_key=KEY)
        second = reopened.claim_review(SESSION, expected_fence=first['fence'], now=NOW + 11, ttl=10)
        self.assertGreater(second['fence'], first['fence'])
        self.assertNotEqual(second['token'], first['token'])
        with self.assertRaises(ReviewLedgerRejected):
            reopened.release_review(SESSION, token=first['token'], fence=first['fence'], now=NOW + 12)
        self.assertFalse(second['execution_authorized'])
        self.assertNotIn(second['token'], json.dumps(self.store.read()[0]))

    def test_cancellation_refund_and_revocation_invalidate_lease_and_remain_blocking(self):
        self.create()
        claim = self.journal.claim_review(SESSION, expected_fence=1, now=NOW, ttl=10)
        for reason in ('cancelled', 'refund_or_dispute', 'owner_revoked', 'repair_failed'):
            held = self.journal.hold(SESSION, reason=reason, now=NOW + 1)
            before = self.store.read()
            again = self.journal.hold(SESSION, reason=reason, now=NOW + 2)
            self.assertEqual(again['status'], 'already_recorded')
            self.assertEqual(self.store.read(), before)
            self.assertFalse(held['execution_authorized'])
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.release_review(SESSION, token=claim['token'], fence=claim['fence'], now=NOW + 3)
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.claim_review(SESSION, expected_fence=held['fence'], now=NOW + 12, ttl=10)
        result = self.journal.delivery_review(SESSION, now=NOW + 12)
        self.assertFalse(result['delivery_authorized'])
        self.assertIn('private_execution_unadmitted', result['blockers'])
        self.assertEqual(set(result['hold_reasons']), {'cancelled', 'refund_or_dispute', 'owner_revoked', 'repair_failed'})

    def test_durable_stale_write_and_privacy_loss_fail_closed(self):
        self.create(); state, revision = self.store.read()
        self.store.write(state, revision)
        with self.assertRaises(ReviewLedgerRejected):
            self.store.write(state, revision)
        self.path.chmod(0o644)
        try:
            with self.assertRaises(ReviewLedgerRejected): self.store.read()
        finally:
            self.path.chmod(0o600)
        with self.assertRaises(ReviewLedgerRejected):
            scope_module.SQLiteScopeReviewStore(self.review.path)

    def test_invalid_budget_corruption_and_stale_scope_never_prepare_delivery(self):
        self.create()
        for ttl in (True, 0, 301):
            with self.assertRaises(ReviewLedgerRejected):
                self.journal.claim_review(SESSION, expected_fence=1, now=NOW, ttl=ttl)
        with self.assertRaises(ReviewLedgerRejected):
            self.journal.claim_review(SESSION, expected_fence=1, now=NOW + 3601, ttl=10)
        result = self.journal.delivery_review(SESSION, now=NOW + 3601)
        self.assertFalse(result['delivery_authorized'])
        self.assertIn('scope_approval_expired', result['blockers'])
        state, rev = self.store.read(); broken = copy.deepcopy(state)
        broken['plans'][0]['execution_authorized'] = True
        with self.assertRaises(ReviewLedgerRejected): self.store.write(broken, rev)

    def test_owner_key_mismatch_cannot_claim_cached_scope(self):
        self.create()
        other = scope_module.PaidScopeReview(self.store, self.review,
                                            approval_key=b'other-owner-key-32-bytes-xxxx!!!!!')
        with self.assertRaises(ReviewLedgerRejected):
            other.claim_review(SESSION, expected_fence=1, now=NOW, ttl=10)

    def test_event_exhaustion_reserves_space_for_all_safety_holds(self):
        self.create()
        fence, timestamp = 1, NOW
        while True:
            try:
                claim = self.journal.claim_review(SESSION, expected_fence=fence, now=timestamp, ttl=1)
                fence, timestamp = claim['fence'], timestamp + 2
            except ReviewLedgerRejected:
                break
        for reason in ('cancelled', 'refund_or_dispute', 'owner_revoked', 'repair_failed'):
            held = self.journal.hold(SESSION, reason=reason, now=timestamp)
            self.assertFalse(held['execution_authorized'])
        self.assertEqual(len(self.store.read()[0]['plans'][0]['events']), 32)

    def test_two_private_coordinators_cannot_hold_simultaneous_review_claims(self):
        self.create()
        other_session = 'f' * 64
        reviews, rev = self.review.read()
        reviews['orders'].append({**reviews['orders'][0], 'session_sha256': other_session})
        self.review.write(reviews, rev)
        self.journal.record_scope(other_session, approval(session_sha256=other_session), now=NOW)
        stores = [scope_module.SQLiteScopeReviewStore(self.path) for _ in range(2)]
        workers = [scope_module.PaidScopeReview(store, self.review, approval_key=KEY) for store in stores]
        barrier = threading.Barrier(2)
        original_reads = [store.read for store in stores]
        def barrier_read(index):
            result = original_reads[index]()
            barrier.wait(timeout=3)
            return result
        def claim(index):
            try:
                workers[index].claim_review((SESSION, other_session)[index], expected_fence=1, now=NOW, ttl=10)
                return 'claimed'
            except ReviewLedgerRejected:
                return 'rejected'
        with patch.object(stores[0], 'read', side_effect=lambda: barrier_read(0)), \
                patch.object(stores[1], 'read', side_effect=lambda: barrier_read(1)), \
                ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, range(2)))
        self.assertCountEqual(results, ['claimed', 'rejected'])
        self.assertEqual(sum(plan['lease'] is not None for plan in self.store.read()[0]['plans']), 1)


if __name__ == '__main__':
    unittest.main()
