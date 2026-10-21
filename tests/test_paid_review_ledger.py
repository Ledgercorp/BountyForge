"""Offline proof that one Stripe payment never becomes two work orders."""
import copy
import hashlib
import os
import unittest
from unittest.mock import patch

from bountyforge.stripe_order_gate import StripeOrderGate, OrderNotVerified
from bountyforge.paid_review_ledger import PaidReviewLedger, ReviewLedgerRejected

SESSION = 'cs_live_' + 's'*26
DIGEST = hashlib.sha256(SESSION.encode('ascii')).hexdigest()
ENV = {'STRIPE_SECRET_KEY': 'rk_live_' + 'k'*30,
       'BOUNTYFORGE_APPROVED_PAYMENT_LINK': 'plink_' + 'l'*26,
       'BOUNTYFORGE_APPROVED_AMOUNT_CENTS': '4900'}


def evidence(**override):
    data = {'schema': 1, 'kind': 'stripe_payment_review_evidence',
            'checkout_session_sha256': DIGEST, 'payment_verified': True,
            'execution_authorized': False, 'outside_submission_authorized': False,
            'service': 'python_bugfix_basic', 'currency': 'usd', 'amount_cents': 4900,
            'verified_at': '2026-10-21T16:00:00+00:00'}
    data.update(override)
    return data


class Store:
    def __init__(self):
        self.value = None
        self.version = None
        self.writes = 0
        self.conflict = False
    def read(self):
        return copy.deepcopy(self.value), self.version
    def write(self, state, expected):
        if self.conflict or expected != self.version:
            raise ReviewLedgerRejected('CAS conflict')
        self.value = copy.deepcopy(state)
        self.writes += 1
        self.version = str(self.writes)


class PaidReviewTests(unittest.TestCase):
    def build(self):
        with patch.dict(os.environ, ENV, clear=True):
            return PaidReviewLedger(Store(), StripeOrderGate())

    def test_new_and_repeat_payment_only_one_review(self):
        worker = self.build()
        with patch.object(StripeOrderGate, 'verify', return_value=evidence()) as verifier:
            first = worker.review_payment(SESSION)
            again = worker.review_payment(SESSION)
        self.assertEqual(verifier.call_count, 2)
        self.assertEqual(first['status'], 'awaiting_owner_scope_review')
        self.assertEqual(again['status'], 'already_recorded')
        self.assertEqual(worker.store.writes, 1)
        self.assertEqual(len(worker.store.value['orders']), 1)
        self.assertNotIn(SESSION, str(worker.store.value))
        self.assertFalse(first['execution_authorized'])
        self.assertFalse(again['external_submission_authorized'])

    def test_fresh_refund_verification_precedes_dedupe(self):
        worker = self.build()
        with patch.object(StripeOrderGate, 'verify',
                          side_effect=[evidence(), OrderNotVerified('refunded')]):
            worker.review_payment(SESSION)
            with self.assertRaises(OrderNotVerified):
                worker.review_payment(SESSION)
        self.assertEqual(worker.store.writes, 1)

    def test_cannot_inject_a_fake_model_gate(self):
        with self.assertRaises(ReviewLedgerRejected):
            PaidReviewLedger(Store(), object())

    def test_forged_receipts_fail_without_storage(self):
        for bad in ({'checkout_session_sha256': 'a'*64},
                    {'payment_verified': False}, {'execution_authorized': True},
                    {'outside_submission_authorized': True},
                    {'amount_cents': True}, {'service': 'other'},
                    {'verified_at': '2026-10-21'}):
            with self.subTest(bad=bad):
                worker = self.build()
                with patch.object(StripeOrderGate, 'verify', return_value=evidence(**bad)):
                    with self.assertRaises(ReviewLedgerRejected):
                        worker.review_payment(SESSION)
                self.assertEqual(worker.store.writes, 0)

    def test_conflicting_write_never_admits_work(self):
        worker = self.build()
        worker.store.conflict = True
        with patch.object(StripeOrderGate, 'verify', return_value=evidence()):
            with self.assertRaises(ReviewLedgerRejected):
                worker.review_payment(SESSION)
        self.assertEqual(worker.store.writes, 0)

    def test_unrecognized_or_corrupt_existing_ledgers_fail(self):
        bad_states = (
            {'version': 1, 'jobs': []}, {'version': 1, 'orders': [{'status': 'executing'}]},
            {'version': 2, 'orders': []}, {'version': 1, 'orders': {}},
            {'version': 1, 'orders': [{'session_sha256': 'a'*64}]*101},
        )
        for bad in bad_states:
            with self.subTest(bad=bad):
                worker = self.build()
                worker.store.value, worker.store.version = bad, '1'
                with patch.object(StripeOrderGate, 'verify', return_value=evidence()):
                    with self.assertRaises(ReviewLedgerRejected):
                        worker.review_payment(SESSION)
                self.assertEqual(worker.store.writes, 0)


if __name__ == '__main__':
    unittest.main()
