"""Mock Stripe API evidence. No authenticated API calls, payments or live writes."""
import io
import json
import os
import unittest
from unittest.mock import patch
from bountyforge.stripe_order_gate import StripeOrderGate, OrderNotVerified


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


SESSION_ID = 'cs_live_' + 's' * 26
PAYMENT_ID = 'pi_' + 'p' * 26
LINK_ID = 'plink_' + 'l' * 26
CHARGE_ID = 'ch_' + 'c' * 26
CFG = {
    'STRIPE_SECRET_KEY': 'rk_live_' + 'k' * 30,
    'BOUNTYFORGE_APPROVED_PAYMENT_LINK': LINK_ID,
    'BOUNTYFORGE_APPROVED_AMOUNT_CENTS': '4900',
}


def record(session_overrides=None, payment_overrides=None):
    session = {'id': SESSION_ID, 'livemode': True, 'mode': 'payment',
               'status': 'complete', 'payment_status': 'paid', 'currency': 'usd',
               'amount_total': 4900, 'payment_intent': PAYMENT_ID,
               'payment_link': LINK_ID,
               'metadata': {'bountyforge_service': 'python_bugfix_basic',
                            'contract_version': '1'}}
    intent = {'id': PAYMENT_ID, 'livemode': True, 'status': 'succeeded',
              'currency': 'usd', 'amount_received': 4900, 'amount': 4900,
              'latest_charge': CHARGE_ID}
    charge = {'id': CHARGE_ID, 'livemode': True, 'payment_intent': PAYMENT_ID,
              'status': 'succeeded', 'paid': True, 'captured': True,
              'refunded': False, 'disputed': False,
              'amount_refunded': 0, 'currency': 'usd', 'amount': 4900}
    session.update(session_overrides or {})
    intent.update(payment_overrides or {})
    return session, intent, charge


class StripeOrderGateTests(unittest.TestCase):
    def make_gate(self):
        with patch.dict(os.environ, CFG, clear=True):
            return StripeOrderGate()

    def test_unconfigured_gate_rejects_every_missing_requirement(self):
        for name in CFG:
            values = {k: v for k, v in CFG.items() if k != name}
            with self.subTest(name=name), patch.dict(os.environ, values, clear=True):
                with self.assertRaises(OrderNotVerified):
                    StripeOrderGate()

    def test_invalid_live_session_rejected_before_network(self):
        gate = self.make_gate()
        with patch('urllib.request.build_opener') as build:
            for candidate in ('cs_test_' + 'x' * 26, '../secret',
                              SESSION_ID + '?expand[]=customer',
                              'https://other.example', 'cs_live_/../'):
                with self.subTest(candidate=candidate), self.assertRaises(OrderNotVerified):
                    gate.verify(candidate)
            build.assert_not_called()

    def test_confirmed_order_emits_only_non_dispatchable_evidence(self):
        gate = self.make_gate()
        session, payment, charge = record()
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = [
                Response(json.dumps(record).encode()) for record in (session, payment, charge)]
            result = gate.verify(SESSION_ID)
            calls = build.return_value.open.call_args_list
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[0].args[0].full_url,
                             'https://api.stripe.com/v1/checkout/sessions/' + SESSION_ID)
            self.assertEqual(calls[1].args[0].full_url,
                             'https://api.stripe.com/v1/payment_intents/' + PAYMENT_ID)
            self.assertEqual(calls[2].args[0].full_url,
                             'https://api.stripe.com/v1/charges/' + CHARGE_ID)
        self.assertTrue(result['payment_verified'])
        self.assertEqual(result['amount_cents'], 4900)
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['outside_submission_authorized'])
        self.assertNotIn(SESSION_ID, json.dumps(result))
        self.assertNotIn(PAYMENT_ID, json.dumps(result))

    def test_nonmatching_checkout_never_unlocks_payment(self):
        changes = [
            {'livemode': False}, {'mode': 'subscription'}, {'status': 'open'},
            {'payment_status': 'unpaid'}, {'currency': 'eur'}, {'amount_total': 4800},
            {'amount_total': 5000}, {'payment_link': 'plink_other'},
            {'metadata': {}},
            {'metadata': {'bountyforge_service': 'other', 'contract_version': '1'}},
            {'metadata': {'bountyforge_service': 'python_bugfix_basic', 'contract_version': '9'}}]
        for change in changes:
            session, _, _ = record(session_overrides=change)
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.return_value = Response(json.dumps(session).encode())
                with self.subTest(change=change), self.assertRaises(OrderNotVerified):
                    self.make_gate().verify(SESSION_ID)
                self.assertEqual(build.return_value.open.call_count, 1)

    def test_payment_intent_must_be_independently_paid(self):
        changes = [{'status': 'requires_payment_method'}, {'livemode': False},
                   {'currency': 'cad'}, {'amount_received': 0},
                   {'amount_received': 4800}, {'id': 'pi_wrong'}]
        for change in changes:
            session, payment, charge = record(payment_overrides=change)
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = [
                    Response(json.dumps(x).encode()) for x in (session, payment, charge)]
                with self.subTest(change=change), self.assertRaises(OrderNotVerified):
                    self.make_gate().verify(SESSION_ID)

    def test_refunds_disputes_uncaptured_charges_rejected(self):
        for change in [{'refunded': True}, {'disputed': True}, {'amount_refunded': 100},
                       {'captured': False}, {'paid': False}, {'status': 'failed'},
                       {'id': 'ch_wrong'}]:
            session, payment, charge = record()
            charge.update(change)
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.side_effect = [
                    Response(json.dumps(x).encode()) for x in (session, payment, charge)]
                with self.subTest(change=change), self.assertRaises(OrderNotVerified):
                    self.make_gate().verify(SESSION_ID)

    def test_errors_do_not_echo_secrets(self):
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = Exception(CFG['STRIPE_SECRET_KEY'])
            with self.assertRaises(OrderNotVerified) as caught:
                self.make_gate().verify(SESSION_ID)
            self.assertNotIn(CFG['STRIPE_SECRET_KEY'], str(caught.exception))
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_oversize_provider_response_fails_closed(self):
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = Response(b'x' * 65537)
            with self.assertRaises(OrderNotVerified):
                self.make_gate().verify(SESSION_ID)

    def test_processing_payment_is_not_a_paid_order(self):
        session, payment, charge = record(payment_overrides={'status': 'processing'})
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect = [
                Response(json.dumps(x).encode()) for x in (session, payment, charge)]
            with self.assertRaises(OrderNotVerified):
                self.make_gate().verify(SESSION_ID)


if __name__ == '__main__':
    unittest.main()
