"""Read-only Stripe paid-order evidence gate. Never dispatches or delivers code."""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

SESSION = re.compile(r'cs_live_[a-zA-Z0-9]{20,100}\Z')
PAYMENT = re.compile(r'pi_[a-zA-Z0-9]{12,100}\Z')
CHARGE = re.compile(r'ch_[a-zA-Z0-9]{12,100}\Z')
LINK = re.compile(r'plink_[a-zA-Z0-9]{12,100}\Z')
RESTRICTED_KEY = re.compile(r'rk_live_[a-zA-Z0-9_]{10,256}\Z')
MAX_RESPONSE_BYTES = 65536


class OrderNotVerified(ValueError):
    """Fail closed: absent or inconsistent evidence does not authorize work."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        raise OrderNotVerified('Stripe redirects are not permitted')


class StripeOrderGate:
    """May only run in the trusted coordinator, never in the model or patch sandbox."""

    def __init__(self):
        key = os.environ.get('STRIPE_SECRET_KEY', '')
        link = os.environ.get('BOUNTYFORGE_APPROVED_PAYMENT_LINK', '')
        amount = os.environ.get('BOUNTYFORGE_APPROVED_AMOUNT_CENTS', '')
        if (not RESTRICTED_KEY.fullmatch(key)
                or not LINK.fullmatch(link) or not amount.isdecimal()
                or not 100 <= int(amount) <= 100000):
            raise OrderNotVerified('Stripe payment verification not configured')
        self._key = key
        self._link = link
        self._amount = int(amount)

    def _get(self, group: str, identifier: str) -> dict:
        if group == 'checkout/sessions' and SESSION.fullmatch(identifier):
            pass
        elif group == 'payment_intents' and PAYMENT.fullmatch(identifier):
            pass
        elif group == 'charges' and CHARGE.fullmatch(identifier):
            pass
        else:
            raise OrderNotVerified('Invalid Stripe resource reference')
        request = urllib.request.Request(
            'https://api.stripe.com/v1/' + group + '/' + identifier,
            headers={'Authorization': 'Bearer ' + self._key,
                     'User-Agent': 'BountyForge-PaymentEvidence/1'}, method='GET')
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with opener.open(request, timeout=12) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError('Oversize evidence')
            payload = json.loads(raw)
            if not isinstance(payload, dict) or 'error' in payload:
                raise ValueError('Invalid provider evidence')
            return payload
        except Exception:
            raise OrderNotVerified('Provider evidence unavailable or rejected') from None

    def verify(self, session_id: str) -> dict:
        if not isinstance(session_id, str) or not SESSION.fullmatch(session_id):
            raise OrderNotVerified('Invalid live checkout session reference')
        session = self._get('checkout/sessions', session_id)
        if (session.get('id') != session_id or session.get('livemode') is not True
                or session.get('mode') != 'payment' or session.get('status') != 'complete'
                or session.get('payment_status') != 'paid' or session.get('currency') != 'usd'
                or type(session.get('amount_total')) is not int
                or session['amount_total'] != self._amount
                or session.get('payment_link') != self._link
                or not isinstance(session.get('metadata'), dict)
                or session['metadata'].get('bountyforge_service') != 'python_bugfix_basic'
                or session['metadata'].get('contract_version') != '1'
                or not isinstance(session.get('payment_intent'), str)
                or not PAYMENT.fullmatch(session['payment_intent'])):
            raise OrderNotVerified('Checkout is not an admitted paid service order')
        payment_id = session['payment_intent']
        intent = self._get('payment_intents', payment_id)
        if (intent.get('id') != payment_id or intent.get('livemode') is not True
                or intent.get('status') != 'succeeded' or intent.get('currency') != 'usd'
                or type(intent.get('amount_received')) is not int
                or intent['amount_received'] != self._amount
                or type(intent.get('amount')) is not int or intent['amount'] != self._amount
                or not isinstance(intent.get('latest_charge'), str)
                or not CHARGE.fullmatch(intent['latest_charge'])):
            raise OrderNotVerified('Independent payment evidence rejected')
        charge_id = intent['latest_charge']
        charge = self._get('charges', charge_id)
        if (charge.get('id') != charge_id or charge.get('livemode') is not True
                or charge.get('payment_intent') != payment_id
                or charge.get('status') != 'succeeded'
                or charge.get('paid') is not True or charge.get('captured') is not True
                or charge.get('refunded') is not False or charge.get('disputed') is not False
                or type(charge.get('amount_refunded')) is not int
                or charge['amount_refunded'] != 0
                or charge.get('currency') != 'usd'
                or type(charge.get('amount_captured')) is not int
                or charge['amount_captured'] != self._amount
                or type(charge.get('amount')) is not int
                or charge['amount'] != self._amount):
            raise OrderNotVerified('Charge is absent, incomplete, refunded or disputed')
        return {
            'schema': 1, 'kind': 'stripe_payment_review_evidence',
            'verified_at': datetime.now(timezone.utc).isoformat(),
            'checkout_session_sha256': hashlib.sha256(session_id.encode('ascii')).hexdigest(),
            'service': 'python_bugfix_basic', 'amount_cents': self._amount,
            'currency': 'usd', 'payment_verified': True,
            'work_review_ready': True, 'execution_authorized': False,
            'outside_submission_authorized': False, 'revenue_received_usd': 0,
            'notes': 'Payment evidence only, not scope approval, execution consent or payout.'
        }


def verify_session(gate: StripeOrderGate, session_id: str) -> dict:
    return gate.verify(session_id)
