"""Independent acceptance through CLI processes, files and SQLite connections.

No application functions are imported. All data is fixed owned simulation data.
"""
import hashlib
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from tests.test_phase8_synthetic_order_process import provider

REPO = Path(__file__).resolve().parents[1]
COMMAND = [sys.executable, '-m', 'scripts.phase8_synthetic_order']
SERVICE = [sys.executable, '-m', 'scripts.patch_review_service']
ENV = {'PATH': os.defpath, 'PYTHONPATH': str(REPO),
       'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'}
REQUEST = b'{"session_id":"cs_live_BountyForgeSIMULATIONONLY0001"}'
DATABASE = 'phase8.SIMULATION_ONLY.sqlite3'


class Phase8BlackBoxTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'simulation'
        self.root.mkdir(mode=0o700)
        self.call('init', '--root', str(self.root), expected=0)

    def call(self, *args, data=b'', expected=None, timeout=5):
        completed = subprocess.run(COMMAND + list(args), input=data, cwd=REPO,
                                   env=ENV, capture_output=True, timeout=timeout)
        if expected is not None:
            self.assertEqual(completed.returncode, expected, completed.stderr)
        self.assertNotIn(b'Traceback', completed.stderr)
        return completed

    def run_order(self, port, *args, data=REQUEST, expected=None, timeout=5):
        completed = self.call('run', '--root', str(self.root), '--port', str(port),
                              *args, data=data, expected=expected, timeout=timeout)
        receipt = json.loads(completed.stdout)
        for key in ('real_payment_verified', 'delivery_authorized',
                    'private_execution_authorized', 'customer_source_accepted',
                    'owner_consent_verified', 'stripe_test_mode_verified'):
            self.assertIs(receipt[key], False)
        self.assertEqual(receipt['model_calls'], 0)
        self.assertEqual(receipt['received_revenue_usd'], 0)
        return receipt

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}



    def test_public_journal_is_rejected_before_provider_or_state_change(self):
        with provider() as port:
            self.run_order(port, '--stop-after', 'payment', expected=3)
            journal = self.root / (DATABASE + '-journal')
            journal.write_bytes(b'')
            journal.chmod(0o644)
            before = (self.root / DATABASE).read_bytes()
            result = self.run_order(port, expected=2)
        self.assertEqual(result['provider_requests'], 0)
        self.assertEqual((self.root / DATABASE).read_bytes(), before)
        self.assertEqual(journal.stat().st_mode & 0o777, 0o644)

    def test_hardlinked_journal_is_rejected_and_owner_file_preserved(self):
        with provider() as port:
            self.run_order(port, '--stop-after', 'payment', expected=3)
            sentinel = Path(self.directory.name) / 'owner-file'
            sentinel.write_bytes(b'owner-file-must-remain-exact')
            sentinel.chmod(0o600)
            os.link(sentinel, self.root / (DATABASE + '-journal'))
            result = self.run_order(port, expected=2)
        self.assertEqual(result['provider_requests'], 0)
        self.assertEqual(sentinel.read_bytes(), b'owner-file-must-remain-exact')

    def test_fifo_journal_is_rejected_without_blocking_in_sqlite(self):
        with provider() as port:
            self.run_order(port, '--stop-after', 'payment', expected=3)
            os.mkfifo(self.root / (DATABASE + '-journal'), mode=0o600)
            before = (self.root / DATABASE).read_bytes()
            try:
                result = self.run_order(port, expected=2, timeout=3)
            except subprocess.TimeoutExpired:
                self.fail('FIFO rollback journal blocked real CLI before rejection')
        self.assertEqual(result['provider_requests'], 0)
        self.assertEqual((self.root / DATABASE).read_bytes(), before)



if __name__ == '__main__':
    unittest.main()
