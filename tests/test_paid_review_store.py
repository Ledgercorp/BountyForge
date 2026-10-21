"""Actual private-file CAS, restart, parallel-writer and crash recovery tests."""
import copy
import json
import os
import selectors
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from bountyforge.paid_review_store import SQLitePaidReviewStore
from bountyforge.paid_review_ledger import PaidReviewLedger, ReviewLedgerRejected
from bountyforge.stripe_order_gate import StripeOrderGate
from test_paid_review_ledger import ENV, SESSION, evidence


class PaidStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'paid-review.sqlite3'
        self.store=SQLitePaidReviewStore(self.path)

    def test_restart_preserves_record_and_stale_write_fails(self):
        state={'version':1,'orders':[]}
        self.assertEqual(self.store.read(),(None,None))
        self.assertEqual(self.store.write(state,None),'1')
        second=SQLitePaidReviewStore(self.path)
        self.assertEqual(second.read(),(state,'1'))
        self.assertEqual(second.write(state,'1'),'2')
        with self.assertRaises(ReviewLedgerRejected):self.store.write(state,'1')
        self.assertEqual(self.store.read(),(state,'2'))

    def test_private_payment_state_cannot_be_created_inside_source_checkout(self):
        from bountyforge import paid_review_store
        root=Path(paid_review_store.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root,prefix='.unit-private-reject-') as directory:
            candidate=Path(directory)/'paid.sqlite3'
            with self.assertRaises(ReviewLedgerRejected):SQLitePaidReviewStore(candidate)
            self.assertFalse(candidate.exists())

    def test_two_coordinators_cannot_record_same_payment_twice(self):
        barrier=threading.Barrier(2)
        class ConcurrentStore(SQLitePaidReviewStore):
            def read(inner):
                result=super().read();barrier.wait(timeout=3);return result
        with patch.dict(os.environ,ENV,clear=True):
            workers=[PaidReviewLedger(ConcurrentStore(self.path),StripeOrderGate()) for _ in range(2)]
        def record(worker):
            try:return worker.review_payment(SESSION)['status']
            except ReviewLedgerRejected:return 'cas_rejected'
        with patch.object(StripeOrderGate,'verify',return_value=evidence()),ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(record,workers))
        self.assertCountEqual(results,['awaiting_owner_scope_review','cas_rejected'])
        state,revision=self.store.read()
        self.assertEqual(len(state['orders']),1);self.assertEqual(revision,'1')
        with patch.dict(os.environ,ENV,clear=True):
            reopened=PaidReviewLedger(SQLitePaidReviewStore(self.path),StripeOrderGate())
        with patch.object(StripeOrderGate,'verify',return_value=evidence()):
            self.assertEqual(reopened.review_payment(SESSION)['status'],'already_recorded')
        self.assertEqual(self.store.read()[1],'1')

    def test_private_permissions_symlinks_and_hardlinks_fail_closed(self):
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        self.path.chmod(0o644)
        with self.assertRaises(ReviewLedgerRejected):SQLitePaidReviewStore(self.path)
        self.path.chmod(0o600)
        link=self.path.parent/'linked.sqlite3';link.symlink_to(self.path)
        with self.assertRaises(ReviewLedgerRejected):SQLitePaidReviewStore(link)
        hard=self.path.parent/'hard.sqlite3';os.link(self.path,hard)
        with self.assertRaises(ReviewLedgerRejected):SQLitePaidReviewStore(hard)
        hard.unlink()
        self.path.parent.chmod(0o755)
        try:
            with self.assertRaises(ReviewLedgerRejected):SQLitePaidReviewStore(self.path)
        finally:self.path.parent.chmod(0o700)

    def test_invalid_state_or_revision_never_replaces_existing_value(self):
        state={'version':1,'orders':[]};self.store.write(state,None)
        for revision in ('0','01','../1',True):
            with self.subTest(revision=revision),self.assertRaises(ReviewLedgerRejected):
                self.store.write(state,revision)
        with self.assertRaises(ReviewLedgerRejected):self.store.write({'jobs':[]},'1')
        self.assertEqual(self.store.read(),(state,'1'))

    def test_crash_during_transaction_recovers_without_partial_commit(self):
        state={'version':1,'orders':[]};self.store.write(state,None)
        script=('import sqlite3,sys\n'
                'c=sqlite3.connect(sys.argv[1]);c.execute("BEGIN IMMEDIATE")\n'
                'c.execute("UPDATE paid_review_state SET revision=99,payload=\'{}\' WHERE singleton=1")\n'
                'print("uncommitted",flush=True)\ninput()\n')
        child=subprocess.Popen([sys.executable,'-c',script,str(self.path)],stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout,selectors.EVENT_READ)
                self.assertTrue(selector.select(timeout=3),'Crash probe did not reach transaction')
                self.assertEqual(child.stdout.readline().strip(),b'uncommitted')
            child.kill();child.wait(timeout=3)
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=3)
            child.communicate(timeout=3)
        self.assertEqual(SQLitePaidReviewStore(self.path).read(),(state,'1'))
        self.assertEqual(self.store.write(state,'1'),'2')

    def test_corrupt_persisted_state_is_not_treated_as_empty(self):
        self.store.write({'version':1,'orders':[]},None)
        with sqlite3.connect(self.path) as conn:
            conn.execute('UPDATE paid_review_state SET payload=?', ('{"version":true,"orders":[]}',))
        with self.assertRaises(ReviewLedgerRejected):self.store.read()

    def test_lost_privacy_after_initialization_blocks_each_operation(self):
        state={'version':1,'orders':[]};self.store.write(state,None)
        for target,mode,restore in ((self.path,0o644,0o600),(self.path.parent,0o755,0o700)):
            target.chmod(mode)
            try:
                with self.assertRaises(ReviewLedgerRejected):self.store.read()
                with self.assertRaises(ReviewLedgerRejected):self.store.write(state,'1')
            finally:target.chmod(restore)
        self.assertEqual(self.store.read(),(state,'1'))

    def test_connection_closes_even_when_write_and_rollback_fail(self):
        class Broken:
            closed=False
            def execute(self,*args):raise sqlite3.OperationalError('synthetic I/O failure')
            def rollback(self):raise sqlite3.OperationalError('synthetic rollback failure')
            def close(self):self.closed=True
        broken=Broken()
        with patch.object(self.store,'_connect',return_value=broken):
            with self.assertRaises(ReviewLedgerRejected):self.store.write({'version':1,'orders':[]},None)
        self.assertTrue(broken.closed)
