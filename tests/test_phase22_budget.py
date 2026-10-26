"""Spend decisions exercise actual durable SQLite, never a real API."""
import json
import tempfile
import unittest
from pathlib import Path


class BudgetTests(unittest.TestCase):
    def module(self):
        try: import phase22_budget as m
        except ImportError: self.fail('Fail-closed DeepSeek spending controller is missing')
        return m

    def grant(self, m):
        return {'plan_sha256':'a'*64,'account_sha256':'b'*64,'approved_usd':'2.00',
                'reserve_usd':'20.00','existing_credits_only':True,'no_auto_recharge_confirmed':True,
                'owner_authorized':True,'expires_unix':2000000000}

    def test_missing_or_unconfirmed_grants_cannot_reserve(self):
        m=self.module()
        for field in ('owner_authorized','no_auto_recharge_confirmed','existing_credits_only'):
            grant=self.grant(m);grant[field]=False
            with self.assertRaises(ValueError):m.validate_grant(grant,'a'*64,'b'*64,now=1800000000)
        with self.assertRaises(ValueError):m.validate_grant(None,'a'*64,'b'*64)

    def test_restart_preserves_unknown_requests_and_attempt_cap(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o700)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                first=b.reserve('job_a','22.88',100000);self.assertEqual(first['attempt'],1)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                self.assertEqual(b.status()['committed_microusd'],100000)
                second=b.reserve('job_a','22.88',100000);self.assertEqual(second['attempt'],2)
                with self.assertRaisesRegex(ValueError,'ATTEMPT'):b.reserve('job_a','22.88',1)
                self.assertEqual(b.status()['unknown_requests'],2)

    def test_reserve_and_cumulative_cap_refuse_before_network_dispatch(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o700)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                with self.assertRaisesRegex(ValueError,'RESERVE'):b.reserve('job_a','20.01',20000)
                b.reserve('job_a','22.88',1500000)
                with self.assertRaisesRegex(ValueError,'BUDGET'):b.reserve('job_b','22.88',500001)
                self.assertEqual(b.status()['reserved_requests'],1)

    def test_unknown_cost_never_refunded_and_known_cost_settles_once(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o700)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                r=b.reserve('job_a','22.88',50000);b.settle(r['id'],12000,{'prompt_tokens':10})
                self.assertEqual(b.status()['committed_microusd'],12000)
                with self.assertRaises(ValueError):b.settle(r['id'],0,{})
                r=b.reserve('job_a','22.88',50000)
                with self.assertRaises(ValueError):b.settle(r['id'],50001,{})
                self.assertEqual(b.status()['committed_microusd'],62000)

    def test_one_active_experiment_and_state_identity_are_enforced(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o700)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64):
                with self.assertRaises(ValueError):
                    with m.Budget(store,self.grant(m),'a'*64,'b'*64):pass
            other=self.grant(m);other['plan_sha256']='c'*64
            with self.assertRaises(ValueError):
                with m.Budget(store,other,'c'*64,'b'*64):pass

    def test_unsafe_or_corrupt_store_fails_closed(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o755);store.chmod(0o755)
            with self.assertRaises(ValueError):
                with m.Budget(store,self.grant(m),'a'*64,'b'*64):pass
            store.chmod(0o700);(store/'budget.sqlite').write_text('corrupt');(store/'budget.sqlite').chmod(0o600)
            with self.assertRaises(ValueError):
                with m.Budget(store,self.grant(m),'a'*64,'b'*64):pass

    def test_cancellation_and_total_request_ceiling_survive_reopen(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            store=Path(t)/'private';store.mkdir(mode=0o700)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                for i in range(12):b.reserve('job_'+str(i),'22.88',1)
                with self.assertRaisesRegex(ValueError,'EXPERIMENT_REQUEST_LIMIT'):b.reserve('job_extra','22.88',1)
            with m.Budget(store,self.grant(m),'a'*64,'b'*64) as b:
                (store/'STOP').write_text('stop')
                with self.assertRaisesRegex(ValueError,'STOP'):b.reserve('another','22.88',1)
