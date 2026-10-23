"""Independent acceptance through CLI processes, files and SQLite connections.

No application functions are imported. All data is fixed owned simulation data.
"""
import contextlib
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

    @contextlib.contextmanager
    def recording_provider(self):
        log = Path(self.directory.name) / 'provider-requests.jsonl'
        child = subprocess.Popen([sys.executable, '-m', 'tests.support.phase8_recording_provider', str(log)],
                                 env=ENV, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(timeout=5), 'Recording provider did not start')
            yield json.loads(child.stdout.readline())['port'], log
        finally:
            child.terminate()
            try:
                child.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill(); child.communicate(timeout=3)

    def test_real_receipts_match_independent_sqlite_and_file_evidence(self):
        with self.recording_provider() as (port, log):
            first = self.run_order(port, expected=0)
            before = self.snapshot()
            duplicate = self.run_order(port, expected=0)
            requests = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(requests), 9)
        expected_paths = ['/v1/checkout/sessions/cs_live_BountyForgeSIMULATIONONLY0001',
                          '/v1/payment_intents/pi_BountyForgeSIMULATIONONLY0001',
                          '/v1/charges/ch_BountyForgeSIMULATIONONLY0001']
        self.assertEqual([r['path'] for r in requests], expected_paths * 3)
        for request in requests:
            self.assertEqual(request['method'], 'GET')
            self.assertEqual(request['peer'], '127.0.0.1')
            self.assertFalse(any(k.lower() == 'authorization' for k in request['headers']))
        self.assertEqual(len({r['headers']['X-BountyForge-Simulator-Nonce'] for r in requests}), 9)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((first['provider_requests'], first['independent_owned_replays']), (6, 1))
        self.assertEqual((duplicate['provider_requests'], duplicate['independent_owned_replays']), (3, 0))
        self.assertEqual(first['package_sha256'], duplicate['package_sha256'])
        package = self.root / 'phase8.SIMULATION_ONLY.review.json'
        self.assertEqual(first['package_sha256'], hashlib.sha256(package.read_bytes()).hexdigest())
        with sqlite3.connect(f'file:{self.root / DATABASE}?mode=ro', uri=True) as db:
            jobs = db.execute('SELECT id,step,rev FROM jobs').fetchall()
            events = db.execute('SELECT rev,step FROM events ORDER BY rev').fetchall()
            evidence = db.execute('SELECT record,record_sha256 FROM simulation_only_evidence').fetchall()
            stored_hash = db.execute('SELECT package_sha FROM simulation_only_order').fetchone()[0]
        self.assertEqual(jobs, [('synthetic_0123456789abcdef', 'AWAITING_OWNER_APPROVAL', 4)])
        self.assertEqual([r[0] for r in events], list(range(5)))
        self.assertEqual(stored_hash, first['package_sha256'])
        self.assertEqual(len(evidence), 2)
        for raw, digest in evidence:
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), digest)
            self.assertIs(json.loads(raw)['real_payment_verified'], False)

    def test_malformed_bounded_requests_leave_existing_review_unchanged(self):
        with provider() as port:
            self.run_order(port, expected=0)
            before = self.snapshot()
            for raw in (b'', b'{', b'null', b'[]', b'{}', REQUEST + b'{}',
                        b'{"session_id":"customer_source.py"}',
                        REQUEST[:-1] + b',"source":"OWNED_SECRET_SENTINEL"}', b'x' * 257):
                with self.subTest(raw=raw[:50]):
                    result = self.run_order(port, data=raw, expected=2)
                    self.assertEqual(result['provider_requests'], 0)
                    self.assertEqual(self.snapshot(), before)

    def test_external_sqlite_event_corruption_is_rejected_before_http(self):
        with self.recording_provider() as (port, log):
            self.run_order(port, '--stop-after', 'scope', expected=3)
            with sqlite3.connect(self.root / DATABASE) as db:
                db.execute('UPDATE events SET evidence_sha=? WHERE rev=0', ('0' * 64,))
            before = self.snapshot()
            received = log.read_bytes()
            rejected = self.run_order(port, expected=2)
            self.assertEqual(rejected['reason'], 'ledger_tampered')
            self.assertEqual(rejected['provider_requests'], 0)
            self.assertEqual(log.read_bytes(), received)
            self.assertEqual(self.snapshot(), before)

    def test_corrupt_retained_proof_causes_durable_hold_without_reexecution(self):
        with provider() as port:
            self.run_order(port, '--stop-after', 'verified', expected=3)
            proof = self.root / 'phase8.SIMULATION_ONLY.verification.json'
            original = proof.read_bytes()
            proof.write_bytes(original + b' ')
            rejected = self.run_order(port, expected=2)
            self.assertEqual(rejected['reason'], 'package_tampered')
            self.assertEqual(rejected['state'], 'HELD')
            self.assertEqual(rejected['independent_owned_replays'], 0)
            self.assertFalse((self.root / 'phase8.SIMULATION_ONLY.review.json').exists())
            proof.write_bytes(original)
            retry = self.run_order(port, expected=2)
            self.assertEqual(retry['state'], 'HELD')
            self.assertEqual(retry['provider_requests'], 0)
        with sqlite3.connect(f'file:{self.root / DATABASE}?mode=ro', uri=True) as db:
            self.assertEqual(db.execute('SELECT step FROM jobs').fetchall(), [('HELD',)])
            self.assertEqual(db.execute('SELECT held,reason FROM simulation_only_order').fetchone(),
                             (1, 'package_tampered'))

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

    def test_kill_while_service_waits_on_stdin_then_restart_is_safe(self):
        output = Path(self.directory.name) / 'service'
        output.mkdir(mode=0o700)
        sentinel = output / 'owner-file'
        sentinel.write_bytes(b'preserve')
        command = SERVICE + ['--owned-only-package', '--output-dir', str(output)]
        child = subprocess.Popen(command, cwd=REPO, env=ENV, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            # EOF is intentionally withheld: the documented service pipe boundary
            # must not write until it has established empty stdin.
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                self.assertFalse(selector.select(timeout=.15))
            self.assertIsNone(child.poll())
            self.assertEqual(list(output.iterdir()), [sentinel])
            child.kill()
            child.communicate(timeout=3)
        finally:
            if child.poll() is None:
                child.kill(); child.communicate(timeout=3)
        completed = subprocess.run(command, input=b'', cwd=REPO, env=ENV,
                                   capture_output=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertIs(receipt['delivery_enabled'], False)
        package = output / 'owned-review-package'
        self.assertEqual(receipt['review_sha256'], hashlib.sha256((package / 'review.json').read_bytes()).hexdigest())
        (package / 'repair.patch').write_bytes(b'owned-corruption')
        before = {p.name: p.read_bytes() for p in package.iterdir()}
        duplicate = subprocess.run(command, input=b'', cwd=REPO, env=ENV,
                                   capture_output=True, timeout=5)
        self.assertEqual(duplicate.returncode, 2)
        self.assertEqual({p.name: p.read_bytes() for p in package.iterdir()}, before)
        self.assertEqual(sentinel.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
