"""Private trusted-coordinator command; payment review only, never fulfillment.

Not deployed. No HTTP listener, customer source input, model, test runner,
write-capable provider operation, queue dispatch or delivery is implemented.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from bountyforge.paid_review_ledger import PaidReviewLedger, ReviewLedgerRejected
from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.stripe_order_gate import StripeOrderGate, OrderNotVerified, SESSION


def main(argv=None, *, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description='Private review only; never executes or delivers source')
    parser.add_argument('--store', required=True, type=Path,
                        help='Approved persistent private volume, outside source checkout')
    args = parser.parse_args(argv)
    source = stdin if stdin is not None else sys.stdin.buffer
    destination = stdout if stdout is not None else sys.stdout
    reason = 'review_store_unavailable'
    try:
        # Keep this payment credential in a separate trusted plane. The approved
        # volume flag is a deployment assertion, not proof of persistence/security.
        if (os.environ.get('BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED') != '1'
                or os.environ.get('GITHUB_ACTIONS') == 'true'
                or any(os.environ.get(name) for name in
                       ('GITHUB_TOKEN', 'GH_TOKEN', 'GROQ_API_KEY', 'OPENAI_API_KEY'))):
            raise ReviewLedgerRejected('Private coordinator configuration required')
        reason = 'invalid_review_reference'
        raw = source.read(257)
        if not isinstance(raw, bytes) or len(raw) > 256:
            raise ReviewLedgerRejected('Invalid review input')
        session = raw.decode('ascii').strip()
        if not SESSION.fullmatch(session):
            raise ReviewLedgerRejected('Invalid review input')
        reason = 'payment_not_verified'
        gate = StripeOrderGate()
        reason = 'review_store_unavailable'
        store = SQLitePaidReviewStore(args.store)
        ledger = PaidReviewLedger(store, gate)
        # Always use fresh provider evidence, including for duplicate reviews.
        result = ledger.review_payment(session)
        result.update(schema=1, kind='private_paid_order_review')
        code = 0
    except OrderNotVerified:
        result = {'status': 'rejected', 'reason': 'payment_not_verified'}
        code = 2
    except (ReviewLedgerRejected, OSError, ValueError):
        # No exception text, raw session, path, provider response, PII or secret.
        result = {'status': 'rejected', 'reason': reason}
        code = 2
    result.update(schema=1, kind='private_paid_order_review', execution_authorized=False,
                  external_submission_authorized=False, customer_source_accepted=False,
                  model_calls=0, fulfillment_dispatched=False)
    destination.write(json.dumps(result, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
