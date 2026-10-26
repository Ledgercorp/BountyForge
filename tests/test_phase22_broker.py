"""Provider is simulated only at the outbound HTTPS boundary; no paid calls."""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

KEY='sk-'+'x'*32


class Reply:
    status=200
    def __init__(self,value):self.raw=json.dumps(value).encode()
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def read(self,n):return self.raw[:n]


def completion(**override):
    value={'id':'mock-completion','model':'deepseek-v4-pro','choices':[{'index':0,'finish_reason':'stop',
           'message':{'role':'assistant','content':'{"changes":[{"line":3,"new":"return value"}]}','reasoning_content':'not persisted'}}],
           'usage':{'prompt_tokens':100,'completion_tokens':40,'total_tokens':140,'prompt_cache_hit_tokens':0,
                    'prompt_cache_miss_tokens':100,'completion_tokens_details':{'reasoning_tokens':30}}}
    value.update(override);return value


class BrokerTests(unittest.TestCase):
    def module(self):
        try:import phase22_deepseek as m
        except ImportError:self.fail('Restricted DeepSeek repair broker is missing')
        return m

    def test_only_exact_endpoint_method_pairs_can_use_the_credential(self):
        m=self.module();client=m.DeepSeekClient(KEY)
        with patch.object(client._opener,'open',side_effect=AssertionError('network must not run')):
            for method,path in [('GET','/chat/completions'),('POST','/user/balance'),('GET','https://evil.test/models'),('POST','/files'),('GET','/models?url=evil')]:
                with self.assertRaises(ValueError):client.call(method,path,{})

    def test_redirects_are_not_followed(self):
        m=self.module()
        self.assertIsNone(m.NoRedirect().redirect_request(None,None,302,'m',{},'https://evil.test'))

    def test_provider_usage_is_separate_from_content_and_reasoning_is_not_retained(self):
        m=self.module();r=m.parse_response(completion(),'deepseek-v4-pro')
        self.assertEqual(r['usage']['reasoning_tokens'],30)
        self.assertEqual(r['cost_upper_microusd'],291)
        self.assertNotIn('reasoning_content',json.dumps(r))
        self.assertFalse(r['provider_confirmed_cost'])

    def test_tools_wrong_models_excess_tokens_and_malformed_json_fail_closed(self):
        m=self.module()
        for mutation in ('tools','model','length','usage','duplicate'):
            value=completion()
            if mutation=='tools':value['choices'][0]['message']['tool_calls']=[{'function':{'name':'bash'}}]
            if mutation=='model':value['model']='deepseek-flash'
            if mutation=='length':value['choices'][0]['finish_reason']='length'
            if mutation=='usage':value['usage']['completion_tokens']=5000
            if mutation=='duplicate':value['choices'][0]['message']['content']='{"changes":[],"changes":[]}'
            with self.assertRaises(ValueError):m.parse_response(value,'deepseek-v4-pro')

    def test_client_does_not_print_or_return_error_bodies_or_secret_echoes(self):
        m=self.module();client=m.DeepSeekClient(KEY)
        with patch.object(client._opener,'open',return_value=Reply({'echo':KEY})):
            with self.assertRaisesRegex(ValueError,'SECRET_ECHO'):client.call('GET','/models')

    def test_balance_requires_available_consistent_exact_usd(self):
        m=self.module();value={'is_available':True,'balance_infos':[{'currency':'USD','total_balance':'22.88','granted_balance':'0.00','topped_up_balance':'22.88'}]}
        self.assertEqual(m.usd_balance(value),'22.88')
        value['balance_infos'][0]['total_balance']='22.89'
        with self.assertRaises(ValueError):m.usd_balance(value)
        value['is_available']=False
        with self.assertRaises(ValueError):m.usd_balance(value)

    def test_no_grant_means_no_billable_post_even_with_valid_credential(self):
        m=self.module();client=m.DeepSeekClient(KEY)
        with patch.object(client._opener,'open',side_effect=AssertionError('network must not run')):
            with self.assertRaisesRegex(ValueError,'AUTHORIZED_BUDGET'):client.generate(None,'job',[],'deepseek-v4-pro')

    def test_timeout_reservation_survives_and_retry_is_not_automatic(self):
        m=self.module();import phase22_budget as b
        grant={'plan_sha256':'a'*64,'account_sha256':hashlib.sha256(KEY.encode()).hexdigest(),'approved_usd':'2.00','reserve_usd':'20.00',
               'existing_credits_only':True,'no_auto_recharge_confirmed':True,'owner_authorized':True,'expires_unix':2000000000}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'store';p.mkdir(mode=0o700)
            with b.Budget(p,grant,'a'*64,hashlib.sha256(KEY.encode()).hexdigest()) as budget:
                c=m.DeepSeekClient(KEY);balance={'is_available':True,'balance_infos':[{'currency':'USD','total_balance':'22.88','granted_balance':'0.00','topped_up_balance':'22.88'}]}
                def open_request(req,**kwargs):
                    if req.method=='GET':return Reply(balance)
                    raise TimeoutError('fake-key-in-error-'+KEY)
                with patch.object(c._opener,'open',side_effect=open_request):
                    with self.assertRaisesRegex(ValueError,'PROVIDER_REQUEST_UNCERTAIN'):
                        c.generate(budget,'job',[{'role':'system','content':'JSON only'},{'role':'user','content':'owned task'}],'deepseek-v4-pro')
                self.assertEqual(budget.status()['reserved_requests'],1)
                self.assertEqual(budget.status()['unknown_requests'],1)
                self.assertEqual(budget.status()['committed_microusd'],37848)

    def test_returned_usage_is_accounted_even_when_patch_is_invalid(self):
        m=self.module();import phase22_budget as b
        grant={'plan_sha256':'a'*64,'account_sha256':hashlib.sha256(KEY.encode()).hexdigest(),'approved_usd':'2.00','reserve_usd':'20.00',
               'existing_credits_only':True,'no_auto_recharge_confirmed':True,'owner_authorized':True,'expires_unix':2000000000}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'store';p.mkdir(mode=0o700)
            with b.Budget(p,grant,'a'*64,hashlib.sha256(KEY.encode()).hexdigest()) as budget:
                c=m.DeepSeekClient(KEY)
                balance={'is_available':True,'balance_infos':[{'currency':'USD','total_balance':'22.88','granted_balance':'0.00','topped_up_balance':'22.88'}]}
                value=completion();value['choices'][0]['message']['content']='{"changes":[],"changes":[]}'
                with patch.object(c._opener,'open',side_effect=lambda req,**_:Reply(balance if req.method=='GET' else value)):
                    with self.assertRaises(ValueError):c.generate(budget,'job',[{'role':'system','content':'JSON only'},{'role':'user','content':'owned task'}],'deepseek-v4-pro')
                self.assertEqual(budget.status()['unknown_requests'],0)
                self.assertEqual(budget.status()['committed_microusd'],291)
                self.assertNotIn(KEY,json.dumps(c.last_evidence))

    def test_raw_billable_call_cannot_bypass_budget(self):
        m=self.module();c=m.DeepSeekClient(KEY)
        with patch.object(c._opener,'open',side_effect=AssertionError('must not dispatch')):
            with self.assertRaisesRegex(ValueError,'AUTHORIZED_BUDGET'):c.call('POST','/chat/completions',{'model':'deepseek-v4-pro'})

    def test_prompt_cannot_contain_the_provider_credential(self):
        m=self.module();import phase22_budget as b
        grant={'plan_sha256':'a'*64,'account_sha256':hashlib.sha256(KEY.encode()).hexdigest(),'approved_usd':'2.00','reserve_usd':'20.00',
               'existing_credits_only':True,'no_auto_recharge_confirmed':True,'owner_authorized':True,'expires_unix':2000000000}
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'store';p.mkdir(mode=0o700)
            with b.Budget(p,grant,'a'*64,hashlib.sha256(KEY.encode()).hexdigest()) as budget:
                c=m.DeepSeekClient(KEY)
                with patch.object(c._opener,'open',side_effect=AssertionError('secret must never leave as prompt')):
                    with self.assertRaisesRegex(ValueError,'CREDENTIAL_IN_PROMPT'):
                        c.generate(budget,'job',[{'role':'system','content':'JSON only'},{'role':'user','content':KEY}],'deepseek-v4-pro')
                self.assertEqual(budget.status()['reserved_requests'],0)

    def test_rejected_pre_dispatch_body_is_distinguished_from_a_sent_request(self):
        m=self.module();c=m.DeepSeekClient(KEY)
        self.assertEqual(getattr(c,'completion_requests_dispatched',None),0)
        with self.assertRaises(ValueError):c.call('POST','/chat/completions',{})
        self.assertEqual(c.completion_requests_dispatched,0)
