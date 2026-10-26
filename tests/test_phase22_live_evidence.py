"""Recorded real provider evidence; no inference and no candidate changes."""
import copy
import json
from pathlib import Path
import unittest
from bountyforge.repair_engines import receipt_hash

ROOT=Path(__file__).resolve().parents[1]


class LiveEvidenceTests(unittest.TestCase):
    def module(self):
        try:import phase22_evidence as m
        except ImportError:self.fail('Cross-checked real DeepSeek repair measurement is missing')
        return m

    def records(self):
        return (json.loads((ROOT/'evidence/phase22/deepseek-pro-trial.json').read_text()),
                json.loads((ROOT/'evidence/phase22/live-ledger-summary.json').read_text()))

    def test_actual_success_counts_and_tokens_are_usage_bound(self):
        m=self.module();r,l=self.records();s=m.analyze(r,l)
        self.assertEqual(s['tasks_attempted'],6);self.assertEqual(s['verified_repairs'],6)
        self.assertEqual(s['first_attempt_successes'],6);self.assertEqual(s['retry_assisted_successes'],0)
        self.assertEqual(s['actual_http_completion_attempts'],6)
        self.assertEqual(s['usage']['prompt_tokens'],4983)
        self.assertEqual(s['usage']['completion_tokens'],10647)
        self.assertEqual(s['usage']['reasoning_tokens'],10310)
        self.assertEqual(s['accounted_peak_cost_upper_microusd'],48742)
        self.assertIsNone(s['provider_confirmed_per_request_cost'])
        self.assertFalse(s['independent_unseen_evaluation'])

    def test_rehashed_claim_cannot_hide_missing_or_failed_independent_replay(self):
        m=self.module()
        for mode in ('missing','failed','fewer_tests'):
            r,l=self.records();v=r['cases'][0]['attempts'][0]['verification']
            if mode=='missing':v.pop('independent')
            if mode=='failed':v['independent']['passed']=False
            if mode=='fewer_tests':v['independent']['tests_run']=7
            v['receipt_sha256']=receipt_hash(v);r['receipt_sha256']=receipt_hash(r)
            with self.assertRaises(ValueError):m.analyze(r,l)

    def test_provider_candidate_and_private_ledger_identity_cannot_be_substituted(self):
        m=self.module()
        for mode in ('candidate','ledger_case','tokens'):
            r,l=self.records()
            if mode=='candidate':r['cases'][0]['attempts'][0]['generation']['returned_candidate']='{"changes":[]}'
            if mode=='ledger_case':l['requests'][0]['case_id']='other'
            if mode=='tokens':l['requests'][0]['usage']['completion_tokens']=1
            r['receipt_sha256']=receipt_hash(r);l['receipt_sha256']=receipt_hash(l)
            with self.assertRaises(ValueError):m.analyze(r,l)

    def test_replay_requires_explicit_admission_and_never_starts_provider(self):
        m=self.module()
        with self.assertRaisesRegex(ValueError,'EXPLICIT_RECORDED'):m.replay(False)

    def test_rehashed_usage_cannot_claim_impossible_reasoning_or_cache_totals(self):
        m=self.module()
        for mode in ('reasoning','cache'):
            r,l=self.records();g=r['cases'][0]['attempts'][0]['generation']
            if mode=='reasoning':g['usage']['reasoning_tokens']=99999
            else:g['usage']['prompt_cache_hit_tokens']=99999
            l['requests'][0]['usage']=copy.deepcopy(g['usage'])
            r['receipt_sha256']=receipt_hash(r);l['receipt_sha256']=receipt_hash(l)
            with self.assertRaises(ValueError):m.analyze(r,l)
