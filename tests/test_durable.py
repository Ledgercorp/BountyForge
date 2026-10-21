import json
import tempfile
import unittest
from pathlib import Path
from bountyforge.durable import DurableLedger, Conflict

REV='a'*40
URL='https://github.com/example/project/issues/1'

class Store:
    def __init__(self): self.state=None;self.version=0
    def read(self): return json.loads(json.dumps(self.state)),str(self.version)
    def write(self,state,expected):
        if expected != str(self.version): raise Conflict('stale write')
        self.state=json.loads(json.dumps(state));self.version+=1

class DurableTests(unittest.TestCase):
    def setUp(self): self.store=Store();self.ledger=DurableLedger(self.store)
    def test_discoveries_deduplicate_without_execution_authority(self):
        self.ledger.discover([URL,URL]);self.ledger.discover([URL])
        state,_=self.store.read();self.assertEqual(len(state['discoveries']),1)
        self.assertFalse(state['discoveries'][0]['execution_authorized'])
    def test_one_claim_across_independent_runners_and_idempotent_enqueue(self):
        self.assertTrue(self.ledger.enqueue_synthetic(REV,'2026-10-21'))
        self.assertFalse(self.ledger.enqueue_synthetic(REV,'2026-10-21'))
        first=self.ledger.claim();self.assertIsNotNone(first)
        second=DurableLedger(self.store)
        second.enqueue_synthetic(REV,'2026-10-22')
        self.assertIsNone(second.claim())
    def test_interrupted_job_recovers_and_old_completion_is_rejected(self):
        self.ledger.enqueue_synthetic(REV,'2026-10-21');first=self.ledger.claim()
        state,version=self.store.read();state['jobs'][0]['lease_until']=0;self.store.write(state,version)
        second=self.ledger.claim()
        self.assertEqual(second['attempts'],2)
        self.assertFalse(self.ledger.finish_failed(first,'interrupted'))
        self.assertTrue(self.ledger.finish_failed(second,'test_failure'))
        self.assertEqual(self.store.state['jobs'][0]['state'],'failed')
    def test_compare_and_swap_rejects_conflicting_snapshots(self):
        self.ledger.enqueue_synthetic(REV,'2026-10-21')
        a,version=self.store.read();b,_=self.store.read()
        self.store.write(a,version)
        with self.assertRaises(Conflict): self.store.write(b,version)
    def test_no_arbitrary_job_source_or_revision(self):
        for revision in ('main','../../secrets','b'*39):
            with self.assertRaises(ValueError):self.ledger.enqueue_synthetic(revision,'2026-10-21')
    def test_unknown_or_oversized_state_fails_closed(self):
        self.store.state={'version':1,'jobs':[{'input_json':'arbitrary'}]}
        with self.assertRaises(ValueError):self.ledger.claim()
