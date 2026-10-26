import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bountyforge.repair_engines import encoded


class RevenueTests(unittest.TestCase):
    def module(self):
        try:from bountyforge import crypto_revenue as m
        except ImportError:self.fail('Crypto research coordination and review-only earnings ledger are missing')
        return m

    def test_advertised_and_awarded_assets_are_not_received_earnings_after_restart(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'crypto.sqlite';s=m.CryptoReviewStore(p);ledger=m.CryptoLedger(s,mode='SIMULATED')
            ledger.record_status('example','AWARDED_REPORTED','USDC','100',source='https://superteam.fun/earn/listing/example')
            again=m.CryptoLedger(m.CryptoReviewStore(p),mode='SIMULATED')
            report=again.summary();self.assertEqual(report['reported_awards']['USDC'],'100')
            self.assertEqual(report['confirmed_real_earnings_usd'],'0')
            self.assertEqual(report['received_assets'],{})
            with self.assertRaises(ValueError):m.CryptoLedger(s,mode='OBSERVE_ONLY')

    def test_cas_stale_revision_and_duplicate_transaction_never_double_credit(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            s=m.CryptoReviewStore(Path(t)/'crypto.sqlite');l=m.CryptoLedger(s,mode='SIMULATED')
            state,rev=s.read_crypto();self.assertTrue(s.write_crypto(state,rev));self.assertFalse(s.write_crypto(state,rev))
            proof={'kind':'SOLANA_FINALIZED_NET_RECEIPT','signature':'3'*88,'wallet':'2'*32,'asset':'USDC','amount_base_units':1000000,'decimals':6,'slot':10}
            self.assertTrue(l.record_simulated_payment('example',proof))
            self.assertFalse(l.record_simulated_payment('another',proof))
            self.assertEqual(l.summary()['simulated_received_assets']['USDC'],'1')
            self.assertEqual(l.summary()['confirmed_real_earnings_usd'],'0')

    def test_caller_receipt_and_approval_booleans_cannot_invent_real_payments(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            l=m.CryptoLedger(m.CryptoReviewStore(Path(t)/'crypto.sqlite'),mode='OBSERVE_ONLY')
            with self.assertRaises(ValueError):l.record_payment('x',{'verified':True},'3'*88,'USDC',{'owner_approved':True})
            with self.assertRaises(ValueError):l.record_simulated_payment('x',{})

    def test_signed_review_binds_exact_package_but_cannot_authorize_live_submission(self):
        m=self.module();key=b'test-only-owner-review-key-32-bytes'
        package={'opportunity_id':'example','commercial_admission':'NOT_ADMITTED'}
        package['package_sha256']=hashlib.sha256(encoded(package)).hexdigest()
        payload={'purpose':'BOUNTYFORGE_SUBMISSION_REVIEW','package_sha256':package['package_sha256'],'opportunity_id':'example','expires_unix':2000000000}
        approval={'payload':payload,'signature':hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()}
        self.assertTrue(m.verify_owner_review(package,approval,key))
        with self.assertRaises(ValueError):m.verify_owner_review({**package,'package_sha256':'b'*64},approval,key)
        with self.assertRaisesRegex(ValueError,'COMMERCIAL_NOT_ADMITTED'):m.submit_external(package,approval,key)

    def test_dry_run_does_not_attach_synthetic_repairs_to_real_opportunities(self):
        m=self.module();o={'provider':'superteam','id':'example','source_url':'https://superteam.fun/earn/listing/example','observed_at':'2026-10-26T00:00:00Z','availability':'OPEN','ai_agent_eligibility':'ALLOWED'}
        report=m.submission_preview(o,{'classification':'OWNED_DEVELOPMENT','independently_verified':True},now='2026-10-26T00:00:00Z')
        self.assertFalse(report['submission_authorized']);self.assertIn('OWNED_FIXTURE_IS_NOT_REAL_ASSIGNMENT',report['blockers'])

    def test_research_queue_lease_recovery_fences_stale_finish(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            q=m.ResearchQueue(Path(t)/'research.sqlite')
            data={'provider':'superteam','id':'example','source_url':'https://superteam.fun/earn/listing/example'}
            self.assertTrue(q.enqueue_opportunity(data));self.assertFalse(q.enqueue_opportunity(data))
            first=q.claim(5);q.conn.execute("UPDATE jobs SET lease_until=0 WHERE id=?",(first['id'],))
            second=q.claim(5);self.assertNotEqual(first['lease_token'],second['lease_token'])
            self.assertFalse(q.finish(first['id'],{'status':'failed','reason':'QUALIFICATION_BLOCKED'},lease_token=first['lease_token']))
            self.assertTrue(q.finish(second['id'],{'status':'failed','reason':'QUALIFICATION_BLOCKED'},lease_token=second['lease_token']))
            q.close()

    def test_changed_submission_contents_cannot_reuse_the_same_signed_review(self):
        m=self.module();key=b'test-only-owner-review-key-32-bytes'
        o={'provider':'superteam','id':'example','source_url':'https://superteam.fun/earn/listing/example','observed_at':'2026-10-26T00:00:00Z','availability':'OPEN','ai_agent_eligibility':'ALLOWED'}
        package=m.submission_preview(o,now='2026-10-26T00:00:00Z')
        payload={'purpose':'BOUNTYFORGE_SUBMISSION_REVIEW','package_sha256':package['package_sha256'],'opportunity_id':'example','expires_unix':2000000000}
        review={'payload':payload,'signature':hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()}
        package['source_url']='https://superteam.fun/earn/listing/different'
        with self.assertRaises(ValueError):m.verify_owner_review(package,review,key)

    def test_unknown_operating_costs_do_not_turn_into_zero_net_earnings(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            l=m.CryptoLedger(m.CryptoReviewStore(Path(t)/'crypto.sqlite'),mode='SIMULATED')
            self.assertIsNone(l.summary()['net_realized_usd'])

    def test_simulation_storage_cannot_be_rehashed_into_real_payment_authority(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            s=m.CryptoReviewStore(Path(t)/'crypto.sqlite');l=m.CryptoLedger(s,mode='SIMULATED')
            l.record_simulated_payment('x',{'kind':'SOLANA_FINALIZED_NET_RECEIPT','signature':'3'*88,'wallet':'2'*32,'asset':'SOL','amount_base_units':10,'decimals':9,'slot':10})
            state,revision=s.read_crypto();state['payments'][0]['simulated']=False
            with self.assertRaises(ValueError):s.write_crypto(state,revision)

    def test_cost_observations_remain_distinct_from_provider_confirmed_costs(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            l=m.CryptoLedger(m.CryptoReviewStore(Path(t)/'crypto.sqlite'),mode='SIMULATED')
            self.assertTrue(l.record_cost('phase22','0.048742','a'*64))
            self.assertFalse(l.record_cost('phase22','0.048742','a'*64))
            l.record_cost('phase22','0.03','b'*64,basis='DISPLAYED_ACCOUNT_DECREASE')
            s=l.summary();self.assertEqual(len(s['cost_observations']),2)
            self.assertIsNone(s['actual_operating_cost_usd']);self.assertIsNone(s['net_realized_usd'])

    def test_read_only_confirmation_loss_is_uncertain_not_a_second_or_fake_payment(self):
        m=self.module()
        from bountyforge.crypto_receipts import SolanaReadOnly
        from contextlib import contextmanager
        key=b'test-only-application-owner-review-key'
        payload={'purpose':'BOUNTYFORGE_PUBLIC_WALLET_BINDING','expires_unix':2000000000,'wallet':'2'*32,'network':'solana-mainnet'}
        binding={'payload':payload,'signature':hmac.new(key,encoded(payload),hashlib.sha256).hexdigest()}
        tx={'slot':10,'transaction':{'signatures':['3'*88],'message':{'accountKeys':['4'*32,'2'*32]}},'meta':{'err':None,'preBalances':[100,0],'postBalances':[90,10]}}
        phase={'missing':False}
        @contextmanager
        def opened(req,**_):
            data=json.loads(req.data)
            result=(None if phase['missing'] else tx) if data['method']=='getTransaction' else {'value':[{'slot':10,'err':None,'confirmationStatus':'finalized'}]}
            class Response:
                def read(self,n):return json.dumps({'jsonrpc':'2.0','id':data['id'],'result':result}).encode()
            yield Response()
        with tempfile.TemporaryDirectory() as t:
            s=m.CryptoReviewStore(Path(t)/'crypto.sqlite');l=m.CryptoLedger(s,mode='OBSERVE_ONLY',owner_review_key=key);reader=SolanaReadOnly()
            with patch.object(reader.opener,'open',side_effect=opened):
                self.assertTrue(l.record_payment('owned-protocol-test',reader,'3'*88,'SOL',binding))
                self.assertEqual(l.summary()['received_assets'],{'SOL':'0.00000001'})
                self.assertIsNone(l.summary()['spendable_usd'])
                state,_=s.read_crypto();phase['missing']=True;l.recheck_payment(state['payments'][0]['id'],reader)
                self.assertEqual(l.summary()['received_assets'],{})
                state,_=s.read_crypto();self.assertEqual(len(state['payments'][0]['observations']),2)
                self.assertEqual(state['payments'][0]['current_confirmation'],'UNCONFIRMED_OR_UNAVAILABLE')
