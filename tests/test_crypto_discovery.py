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

    def test_owner_key_file_requires_private_single_link_owned_regular_file(self):
        import os,tempfile
        from pathlib import Path
        m=self.module();token='agent_mock_123456789012345678901234'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'superteam.key';path.write_text(token+'\n');path.chmod(0o600)
            self.assertEqual(m.load_superteam_api_key(path),token)
            self.assertNotIn(token,str({'path':str(path)}))
            path.chmod(0o640)
            with self.assertRaisesRegex(ValueError,'SUPERTEAM_CREDENTIAL_FILE_REJECTED'):
                m.load_superteam_api_key(path)
            path.chmod(0o600)
            link=Path(directory)/'linked.key';link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,'SUPERTEAM_CREDENTIAL_FILE_REJECTED'):
                m.load_superteam_api_key(link)
            hard=Path(directory)/'hard.key';os.link(path,hard)
            with self.assertRaisesRegex(ValueError,'SUPERTEAM_CREDENTIAL_FILE_REJECTED'):
                m.load_superteam_api_key(path)

    def test_authenticated_superteam_get_is_mocked_and_never_echoes_key(self):
        m=self.module();token='agent_mock_123456789012345678901234';client=m.CryptoReadOnly(token=token);seen=[]
        from contextlib import contextmanager
        import json
        @contextmanager
        def opened(req,**kwargs):
            seen.append(req.get_header('Authorization'))
            class Response:
                status=200
                def read(self,n):return json.dumps([]).encode()
            yield Response()
        with patch.object(client.opener,'open',side_effect=opened):result=client.discover()
        self.assertEqual(seen,['Bearer '+token])
        self.assertEqual(result['status'],'OBSERVED');self.assertEqual(result['opportunities'],[])
        self.assertNotIn(token,str(result))

    def test_authenticated_superteam_401_fails_closed_without_unauthenticated_retry(self):
        m=self.module();token='agent_mock_123456789012345678901234';client=m.CryptoReadOnly(token=token);calls=[]
        import urllib.error
        def denied(request,**kwargs):
            calls.append(request.get_header('Authorization'))
            raise urllib.error.HTTPError(request.full_url,401,'unauthorized',{},None)
        with patch.object(client.opener,'open',side_effect=denied):result=client.discover()
        self.assertEqual(calls,['Bearer '+token]);self.assertEqual(result['status'],'BLOCKED_AUTHENTICATION')
        self.assertIsNone(result['opportunities']);self.assertNotIn(token,str(result))

    def test_github_search_is_a_fixed_unauthenticated_public_get(self):
        m=self.module();c=m.CryptoReadOnly();seen={}
        from contextlib import contextmanager
        import json
        @contextmanager
        def opened(req,**kwargs):
            seen['url']=req.full_url;seen['headers']={k.lower():v for k,v in req.header_items()}
            class Response:
                status=200
                def read(self,n):return json.dumps({'total_count':1,'incomplete_results':False,'items':[
                    {'html_url':'https://github.com/example/project/issues/5','title':'Python bug bounty: $25',
                     'body':'A maintainer advertises a $25 USD bounty. This is an unverified claim.',
                     'state':'open','created_at':'2026-10-01T00:00:00Z','updated_at':'2026-10-26T00:00:00Z',
                     'labels':[{'name':'bounty'}]}]}).encode()
            yield Response()
        with patch.object(c.opener,'open',side_effect=opened):r=c.discover_github()
        self.assertEqual(r['status'],'OBSERVED');self.assertEqual(len(r['opportunities']),1)
        self.assertIn('api.github.com/search/issues?',seen['url']);self.assertNotIn('authorization',seen['headers'])
        item=r['opportunities'][0]
        self.assertEqual(item['availability'],'OPEN');self.assertEqual(item['advertised_amount'],'25')
        self.assertEqual(item['payment_asset'],'USD');self.assertEqual(item['funding_status'],'UNVERIFIED')
        self.assertEqual(item['ai_agent_eligibility'],'UNKNOWN');self.assertFalse(r['complete_scan'])

    def test_github_search_never_accepts_caller_controlled_query_or_rate_limit_as_empty(self):
        m=self.module();c=m.CryptoReadOnly()
        with self.assertRaises(TypeError):c.request('github','search_open_python_bounties',query='bounty')
        import urllib.error
        with patch.object(c.opener,'open',side_effect=urllib.error.HTTPError('url',403,'rate limit',{},None)):
            r=c.discover_github()
        self.assertEqual(r['status'],'RATE_LIMIT_OR_ACCESS_RESTRICTED');self.assertIsNone(r['opportunities'])

    def test_typescript_and_javascript_searches_are_fixed_and_classify_candidates(self):
        import json
        from contextlib import contextmanager
        row={'html_url':'https://github.com/example/project/issues/5','title':'Node bounty $25',
             'body':'Advertised only; funding and eligibility are unknown.','state':'open','labels':[]}
        for lang,profile in [('typescript','TYPESCRIPT'),('javascript','JAVASCRIPT')]:
            client=self.module().CryptoReadOnly();seen=[]
            @contextmanager
            def opened(req,**kwargs):
                seen.append(req.full_url)
                class Response:
                    status=200
                    def read(self,n):return json.dumps({'total_count':1,'incomplete_results':False,'items':[row]}).encode()
                yield Response()
            with patch.object(client.opener,'open',side_effect=opened):result=client.discover_github(language=lang)
            self.assertEqual(result['opportunities'][0]['technical_profile'],profile)
            self.assertIn('PUBLIC_SEARCH_LEADS_ONLY',result['source_role'])
            language_label={'python':'Python','typescript':'TypeScript','javascript':'JavaScript'}[lang]
            self.assertIn('language%3A'+language_label,seen[0])
        client=self.module().CryptoReadOnly()
        with self.assertRaises(ValueError):client.discover_github(language='../../secrets')

    def test_algora_candidate_search_uses_fixed_official_bot_comment_qualifier(self):
        m=self.module();c=m.CryptoReadOnly();seen={}
        from contextlib import contextmanager
        import json
        @contextmanager
        def opened(req,**kwargs):
            seen['url']=req.full_url
            class Response:
                status=200
                headers={'X-RateLimit-Remaining':'20','X-RateLimit-Resource':'search','X-RateLimit-Reset':'1900000000'}
                def read(self,n):return json.dumps({'total_count':0,'incomplete_results':False,'items':[]}).encode()
            yield Response()
        with patch.object(c.opener,'open',side_effect=opened):r=c.discover_github(algora_bot=True)
        self.assertIn('commenter%3Aapp%2Falgora-pbc',seen['url'])
        self.assertEqual(r['query_class'],'ALGORA_BOT_COMMENTER');self.assertEqual(r['total_matches'],0)
        self.assertEqual(r['rate_limit_remaining'],'20');self.assertFalse(r['complete_scan'])

    def test_github_search_excludes_pull_requests_and_rejects_bad_envelopes(self):
        m=self.module();c=m.CryptoReadOnly()
        from contextlib import contextmanager
        import json
        @contextmanager
        def opened(req,**kwargs):
            class Response:
                status=200
                def read(self,n):return json.dumps({'total_count':1,'incomplete_results':False,'items':[
                    {'pull_request':{'url':'https://api.github.com/repos/example/project/pulls/9'},
                     'html_url':'https://github.com/example/project/pull/9','title':'bounty fix','state':'open'}]}).encode()
            yield Response()
        with patch.object(c.opener,'open',side_effect=opened):r=c.discover_github()
        self.assertEqual(r['opportunities'],[]);self.assertEqual(r['pull_requests_excluded'],1)
        with patch.object(c.opener,'open',side_effect=opened):
            c.request= lambda *args,**kwargs:{'status':'OBSERVED','observed_at':'2026-10-26T00:00:00Z','data':{'items':[]}}
            bad=c.discover_github()
        self.assertEqual(bad['status'],'INVALID_RESPONSE');self.assertIsNone(bad['opportunities'])

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
