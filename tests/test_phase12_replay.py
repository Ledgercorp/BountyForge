import importlib
import importlib.util
import json
from pathlib import Path
import unittest

class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('bountyforge.phase12_replay'),
                             'Independent recorded-candidate replay is missing')
        self.api=importlib.import_module('bountyforge.phase12_replay')
        self.raw=(Path(__file__).resolve().parents[1]/'evidence/phase12/codex_live_repairs.json').read_bytes()

    def test_tampered_trace_is_rejected_before_runtime_admission(self):
        class Verifier:
            def preflight(self):raise AssertionError('Must not execute')
        with self.assertRaises(ValueError):
            self.api.replay_recording(self.raw,'0'*64,verifier=Verifier())

    def test_changed_candidate_cannot_hide_behind_recomputed_outer_hash(self):
        data=json.loads(self.raw)
        for call in data['calls']:
            result=call['response'].get('result',{})
            if result.get('content'):
                payload=json.loads(result['content'][0]['text'])
                if payload.get('outcome')=='VERIFIED':
                    payload['candidate']='import os\n'
                    result['content'][0]['text']=json.dumps(payload)
                    break
        raw=json.dumps(data).encode()
        class Verifier:
            def preflight(self):raise AssertionError('Must not execute')
        with self.assertRaises(ValueError):
            self.api.replay_recording(raw,self.api.digest(raw),verifier=Verifier())

if __name__=='__main__':unittest.main()
