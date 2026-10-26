import unittest
from unittest.mock import patch


class DiscoveryTests(unittest.TestCase):
    def module(self):
        try:from bountyforge import crypto_discovery as m
        except ImportError:self.fail('Bounded crypto read-only provider adapter is missing')
        return m

    def test_provider_cannot_register_submit_or_choose_arbitrary_origins(self):
        m=self.module();client=m.CryptoReadOnly()
        with patch.object(client.opener,'open',side_effect=AssertionError('network forbidden')):
            for provider,operation in [('superteam','register'),('superteam','submit'),('onlydust','undocumented_api'),('https://evil.test','listings')]:
                with self.assertRaises(ValueError):client.request(provider,operation)

    def test_documented_superteam_live_endpoint_and_auth_failure_are_not_empty_success(self):
        m=self.module();client=m.CryptoReadOnly()
        import urllib.error
        with patch.object(client.opener,'open',side_effect=urllib.error.HTTPError('url',401,'unauthorized',{},None)):
            r=client.discover()
        self.assertEqual(r['status'],'BLOCKED_AUTHENTICATION')
        self.assertIsNone(r['opportunities']);self.assertEqual(r['account_created'],False)

    def test_redirects_never_forward_provider_credentials(self):
        m=self.module();self.assertIsNone(m.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test'))

    def test_market_quotes_preserve_asset_time_and_do_not_make_withdrawal_guarantees(self):
        m=self.module();c=m.CryptoReadOnly()
        from contextlib import contextmanager
        import json
        @contextmanager
        def opened(req,**kwargs):
            class Response:
                status=200
                def read(self,n):return json.dumps({'price':'200','bid':'199','ask':'201','volume':'100','time':'2026-10-26T00:00:00Z'}).encode()
            yield Response()
        with patch.object(c.opener,'open',side_effect=opened):r=c.market_quote('SOL',now='2026-10-26T00:00:00+00:00')
        self.assertEqual(r['asset'],'SOL');self.assertEqual(r['usd_price'],'200')
        self.assertFalse(r['owner_withdrawal_route_verified']);self.assertFalse(r['guaranteed_liquidity'])
