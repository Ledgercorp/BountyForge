import json
from pathlib import Path
import unittest
from bountyforge.phase13_replay import replay_queue_recording
from bountyforge.repair_engines import digest


class QueueReplayTests(unittest.TestCase):
    def setUp(self):
        self.raw=(Path(__file__).resolve().parents[1]/'evidence/phase13/codex_queue_session.json').read_bytes()

    def test_corrupted_recording_fails_before_runtime(self):
        with self.assertRaises(ValueError):replay_queue_recording(self.raw,'0'*64)

    def test_corrupted_patch_with_rehashed_envelope_still_fails_before_runtime(self):
        recording=json.loads(self.raw)
        for call in recording['calls']:
            if call['tool']=='submit_owned_queue':
                content=call['response']['result']['content'][0]
                value=json.loads(content['text']);value['receipt']['candidate']='import os\n'
                content['text']=json.dumps(value);break
        raw=json.dumps(recording).encode()
        class NoRuntime:
            def preflight(self):raise AssertionError('Tampered input must not execute')
        with self.assertRaises(ValueError):replay_queue_recording(raw,digest(raw),verifier=NoRuntime())
