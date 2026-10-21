"""Review-only paid-order idempotence, using a caller-owned atomic CAS store.

No store backend is configured, no executable jobs are enqueued and no source,
customer identifiers or credentials are retained in this ledger.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime

from bountyforge.stripe_order_gate import StripeOrderGate

MAX_PENDING = 100
_HEX = re.compile(r'[0-9a-f]{64}\Z')


class ReviewLedgerRejected(ValueError):
    pass


def _validate_state(state):
    if (not isinstance(state, dict) or set(state) != {'version', 'orders'}
            or state['version'] != 1 or not isinstance(state['orders'], list)
            or len(state['orders']) > MAX_PENDING):
        raise ReviewLedgerRejected('Unrecognized paid-review ledger')
    seen = set()
    for entry in state['orders']:
        if (not isinstance(entry, dict)
                or set(entry) != {'session_sha256', 'state', 'amount_cents', 'verified_at'}
                or not isinstance(entry['session_sha256'], str)
                or not _HEX.fullmatch(entry['session_sha256'])
                or entry['session_sha256'] in seen
                or entry['state'] != 'awaiting_owner_scope_review'
                or type(entry['amount_cents']) is not int
                or not 100 <= entry['amount_cents'] <= 100000
                or not isinstance(entry['verified_at'], str)):
            raise ReviewLedgerRejected('Invalid or duplicate paid review')
        try:
            timestamp = datetime.fromisoformat(entry['verified_at'])
            if timestamp.utcoffset() is None:
                raise ValueError('Naive timestamp')
        except ValueError as exc:
            raise ReviewLedgerRejected('Invalid verification time') from exc
        seen.add(entry['session_sha256'])


class PaidReviewLedger:
    """The injected store must enforce atomic write(state, expected_version)."""

    def __init__(self, store, gate: StripeOrderGate):
        if type(gate) is not StripeOrderGate:
            raise ReviewLedgerRejected('Trusted StripeOrderGate required')
        self.store, self.gate = store, gate

    def review_payment(self, session_id: str) -> dict:
        # Always independently query fresh live Stripe evidence, even on replay.
        evidence = self.gate.verify(session_id)
        digest = hashlib.sha256(session_id.encode('ascii')).hexdigest()
        if (not isinstance(evidence, dict)
                or evidence.get('schema') != 1
                or evidence.get('kind') != 'stripe_payment_review_evidence'
                or evidence.get('checkout_session_sha256') != digest
                or evidence.get('payment_verified') is not True
                or evidence.get('execution_authorized') is not False
                or evidence.get('outside_submission_authorized') is not False
                or evidence.get('service') != 'python_bugfix_basic'
                or evidence.get('currency') != 'usd'
                or type(evidence.get('amount_cents')) is not int
                or not 100 <= evidence['amount_cents'] <= 100000):
            raise ReviewLedgerRejected('Incomplete payment proof')
        verified = evidence.get('verified_at')
        if not isinstance(verified, str):
            raise ReviewLedgerRejected('Missing verification time')
        try:
            timestamp = datetime.fromisoformat(verified)
            if timestamp.utcoffset() is None:
                raise ValueError('Naive verification time')
        except ValueError as exc:
            raise ReviewLedgerRejected('Invalid verification time') from exc
        state, revision = self.store.read()
        if state is None:
            if revision is not None:
                raise ReviewLedgerRejected('Unversioned paid-review state')
            state = {'version': 1, 'orders': []}
        _validate_state(state)
        if any(x['session_sha256'] == digest for x in state['orders']):
            return {'status': 'already_recorded', 'session_sha256': digest,
                    'execution_authorized': False, 'external_submission_authorized': False}
        if len(state['orders']) >= MAX_PENDING:
            raise ReviewLedgerRejected('Paid-review capacity full')
        state['orders'].append({
            'session_sha256': digest,
            'state': 'awaiting_owner_scope_review',
            'amount_cents': evidence['amount_cents'],
            'verified_at': verified,
        })
        # A rejected CAS is a terminal failure. Never dispatch or retry blindly.
        self.store.write(state, revision)
        return {'status': 'awaiting_owner_scope_review', 'session_sha256': digest,
                'execution_authorized': False, 'external_submission_authorized': False}
