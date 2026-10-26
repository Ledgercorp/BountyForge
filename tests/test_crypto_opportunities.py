import unittest
from datetime import datetime,timezone

NOW='2026-10-26T00:00:00+00:00'


class CryptoOpportunityTests(unittest.TestCase):
    def module(self):
        try:from bountyforge import crypto_opportunities as m
        except ImportError:self.fail('Crypto opportunity normalization and conservative ranking are missing')
        return m

    def listing(self):
        return {'id':'example','slug':'example-python-fix','title':'Python fix','rewardAmount':100,'token':'USDC',
                'deadline':'2026-12-01T00:00:00Z','agentAccess':'AGENT_ALLOWED','status':'OPEN',
                'isWinnersAnnounced':False,'type':'bounty','skills':['Python'],'_count':{'Submission':12}}

    def test_advertisement_is_never_funding_or_eligibility_proof(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        self.assertEqual(item['advertised_amount'],'100')
        self.assertEqual(item['ai_agent_eligibility'],'ALLOWED')
        self.assertEqual(item['funding_status'],'UNVERIFIED')
        self.assertEqual(item['us_eligibility'],'UNKNOWN')
        q=m.qualify_crypto(item,now=NOW)
        self.assertFalse(q['execution_authorized']);self.assertFalse(q['submission_authorized'])
        self.assertIn('FUNDING_UNVERIFIED',q['reasons'])

    def test_human_only_expired_and_deposit_listings_are_not_actionable(self):
        m=self.module()
        for change,reason in [({'agentAccess':'HUMAN_ONLY'},'AI_NOT_EXPLICITLY_ALLOWED'),
                              ({'deadline':'2020-01-01T00:00:00Z'},'CLOSED_OR_EXPIRED'),
                              ({'title':'Pay a registration fee to qualify'},'SCAM_OR_ADVANCE_PAYMENT_SIGNAL')]:
            item=m.normalize_superteam({**self.listing(),**change},NOW)
            self.assertIn(reason,m.qualify_crypto(item,now=NOW)['reasons'])

    def test_unknown_probability_and_fees_never_produce_expected_profit(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        p=m.profitability(item,{'asset':'USDC','usd_price':'1','observed_at':NOW,'volume_24h':'1000','venue':'example'},now=NOW)
        self.assertEqual(p['advertised_gross_usd'],'100')
        self.assertIsNone(p['expected_net_usd']);self.assertIsNone(p['collection_probability'])
        self.assertFalse(p['guaranteed_income'])

    def test_usdc_wrong_mint_and_stale_quotes_are_not_usd_income(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        self.assertFalse(m.asset_identity('USDC','solana-mainnet','fake'))
        p=m.profitability(item,{'asset':'USDC','usd_price':'1','observed_at':'2020-01-01T00:00:00Z','volume_24h':'1000','venue':'example'},now=NOW)
        self.assertIsNone(p['advertised_gross_usd'])
        self.assertIsNone(p['expected_net_usd'])

    def test_duplicate_cross_platform_github_targets_are_quarantined(self):
        m=self.module();a=m.normalize_superteam(self.listing(),NOW);a['github_issue']='https://github.com/a/b/issues/1'
        b=dict(a,provider='github',id='different')
        result=m.deduplicate([a,b])
        self.assertEqual(len(result),1);self.assertEqual(result[0]['coordination_status'],'CONFLICTING_DUPLICATES')

    def test_range_compensation_is_not_falsely_a_fixed_guaranteed_reward(self):
        m=self.module();item=m.normalize_superteam({**self.listing(),'rewardAmount':None,'compensationType':'range','minRewardAsk':10,'maxRewardAsk':100},NOW)
        self.assertIsNone(item['advertised_amount']);self.assertEqual(item['compensation_type'],'range')

    def test_quote_for_another_asset_cannot_value_this_reward(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        p=m.profitability(item,{'asset':'SOL','usd_price':'200','observed_at':NOW,'volume_24h':'1000','venue':'example'},now=NOW)
        self.assertIsNone(p['advertised_gross_usd'])

    def test_currency_mentions_in_an_agents_goal_are_not_advertised_jobs(self):
        m=self.module()
        r=m.normalize_github({'html_url':'https://github.com/example/project/issues/1','state':'open',
            'title':'Agent bootstrap goals','body':'Goal: earn 1 USDC from a bounty.'},NOW)
        self.assertIsNone(r['advertised_amount']);self.assertEqual(r['currency_claim_amount'],'1')

    def test_explicit_usd_amount_is_only_an_advertisement_and_never_funding(self):
        m=self.module();r=m.normalize_github({'html_url':'https://github.com/example/project/issues/2','state':'open',
            'title':'Python bug bounty $25','body':'Bounty: $25 USD. Maintainer decides whether it qualifies.'},NOW)
        self.assertEqual(r['advertised_amount'],'25');self.assertEqual(r['payment_asset'],'USD')
        self.assertEqual(r['funding_status'],'UNVERIFIED')
        self.assertIsNone(r['requirements_untrusted']);self.assertEqual(len(r['issue_body_sha256']),64)
        q=m.qualify_crypto(r,now=NOW)
        self.assertIn('FUNDING_UNVERIFIED',q['reasons']);self.assertIn('AI_NOT_EXPLICITLY_ALLOWED',q['reasons'])
        p=m.profitability(r,now=NOW)
        self.assertEqual(p['advertised_gross_usd'],'25');self.assertIsNone(p['expected_net_usd'])
        self.assertFalse(p['quote_is_cash_realization'])

    def test_ambiguous_github_reward_claim_stays_unknown(self):
        m=self.module();r=m.normalize_github({'html_url':'https://github.com/example/project/issues/3','state':'open',
            'title':'Python fix bounty','body':'Bounty $25 USD; later reward 50 USDC.'},NOW)
        self.assertIsNone(r['advertised_amount']);self.assertEqual(r['payment_asset'],'UNKNOWN')
        self.assertTrue(r['claim_ambiguity'])

    def test_typescript_and_javascript_classifications_do_not_imply_admission(self):
        m=self.module()
        for skills,profile in [(['TypeScript'],'TYPESCRIPT'),(['JavaScript'],'JAVASCRIPT')]:
            item=m.normalize_superteam({**self.listing(),'skills':skills},NOW)
            self.assertEqual(item['technical_profile'],profile)
            gate=m.qualify_crypto(item,now=NOW)
            self.assertNotIn('LANGUAGE_PROFILE_UNVERIFIED',gate['reasons'])
            self.assertFalse(gate['execution_authorized'])
            self.assertFalse(gate['submission_authorized'])

    def test_github_language_profile_is_explicitly_bound_to_fixed_search_hint(self):
        m=self.module();row={'html_url':'https://github.com/example/project/issues/5','state':'open',
            'title':'Python bug bounty $25','body':'Advertised only.'}
        self.assertEqual(m.normalize_github(row,NOW,language_hint='typescript')['technical_profile'],'TYPESCRIPT')
        with self.assertRaises(ValueError):m.normalize_github(row,NOW,language_hint='../../secret')

    def test_unavailable_price_preserves_unknown_value_without_crashing(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        p=m.profitability(item,{'asset':'USDC','usd_price':None,'status':'HTTP_ERROR','observed_at':NOW},now=NOW)
        self.assertIsNone(p['advertised_gross_usd'])

    def test_identical_repeated_discovery_is_deduplicated_without_invented_conflict(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        result=m.deduplicate([item,dict(item)])
        self.assertEqual(result[0]['coordination_status'],'UNIQUE')
        self.assertEqual(result[0]['duplicate_observations'],2)
        self.assertEqual(len(result[0]['records']),1)

    def test_missing_search_state_is_unknown_rather_than_a_claimed_closure(self):
        m=self.module()
        base={'html_url':'https://github.com/example/project/issues/1','title':'Bounty: Python fix','body':'Reward 1 USDC'}
        for value,expected in [(None,'UNKNOWN'),('OPEN','OPEN'),('open','OPEN'),('closed','CLOSED')]:
            item=m.normalize_github({**base,'state':value},NOW)
            self.assertEqual(item['availability'],expected)
            if expected=='UNKNOWN':
                q=m.qualify_crypto(item,now=NOW)
                self.assertIn('AVAILABILITY_UNVERIFIED',q['reasons'])
                self.assertNotIn('CLOSED_OR_EXPIRED',q['reasons'])

    def test_attacker_controlled_decimal_cannot_expand_to_an_unbounded_integer_string(self):
        m=self.module()
        with self.assertRaises(ValueError):m.amount('1e-100000000')
        with self.assertRaises(ValueError):m.amount('1'*1000000)

    def test_work_plan_is_an_unblocking_checklist_and_never_authorizes_execution(self):
        m=self.module();item=m.normalize_superteam(self.listing(),NOW)
        plan=m.research_work_plan(item,m.qualify_crypto(item,now=NOW))
        self.assertEqual(plan['kind'],'CRYPTO_RESEARCH_WORK_PLAN')
        self.assertFalse(plan['execution_authorized']);self.assertIsNone(plan['expected_net_usd'])
        self.assertEqual(plan['steps'][-1]['status'],'OWNER_APPROVAL_REQUIRED')
        with self.assertRaises(ValueError):m.research_work_plan(item,{'execution_authorized':True,'submission_authorized':True})
