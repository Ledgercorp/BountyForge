"""Real subprocess/loopback HTTP/SQLite boundaries; no live payment or model."""
import contextlib
import json
import os
import selectors
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = 'cs_live_BountyForgeSIMULATIONONLY0001'
COMMAND = [sys.executable, '-m', 'scripts.phase8_synthetic_order']
ENV = {'PATH': os.defpath, 'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
       'LC_ALL': 'C.UTF-8'}


@contextlib.contextmanager
def provider(scenario='paid', *, fault=False):
    command = ([sys.executable, '-m', 'tests.support.phase8_provider', scenario] if fault
               else COMMAND + ['provider', '--scenario', scenario])
    child = subprocess.Popen(command, cwd=ROOT, env=ENV,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=5):
                raise AssertionError('Simulator did not become ready')
        line = child.stdout.readline()
        try:
            ready = json.loads(line)
        except ValueError:
            raise AssertionError('Missing simulator implementation: ' + line) from None
        assert ready['provider_simulator'] is True
        yield ready['port']
    finally:
        child.terminate()
        try: child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill(); child.communicate(timeout=3)


class Phase8SyntheticOrderProcessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'owned'
        self.path.mkdir(mode=0o700)
        result = subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, 'Synthetic order workflow missing: '+result.stderr)
        self.assertTrue(json.loads(result.stdout)['provider_simulator'])

    def run_order(self, port, *extra, session=SESSION):
        result = subprocess.run(COMMAND + ['run', '--root', str(self.path), '--port', str(port), *extra],
                                input=json.dumps({'session_id': session}), env=ENV, cwd=ROOT,
                                capture_output=True, text=True, timeout=8)
        data = json.loads(result.stdout)
        self.assertTrue(data['provider_simulator'])
        for name in ('real_payment_verified', 'delivery_authorized', 'private_execution_authorized',
                     'customer_source_accepted', 'stripe_test_mode_verified'):
            self.assertIs(data[name], False)
        self.assertEqual(data['model_calls'], 0)
        self.assertEqual(data['received_revenue_usd'], 0)
        self.assertNotIn(SESSION, result.stdout + result.stderr)
        return result, data

    def test_paid_simulation_completes_review_and_duplicate_rechecks_without_reexecution(self):
        with provider() as port:
            first, data = self.run_order(port)
            self.assertEqual(first.returncode, 0)
            self.assertEqual(data['state'], 'AWAITING_OWNER_APPROVAL')
            self.assertTrue(data['simulated_payment_verified'])
            self.assertEqual(data['provider_requests'], 6)
            self.assertEqual(data['independent_owned_replays'], 1)
            second, duplicate = self.run_order(port)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(duplicate['status'], 'already_reviewed')
        self.assertEqual(duplicate['provider_requests'], 3)
        self.assertEqual(duplicate['independent_owned_replays'], 0)
        packages = list(self.path.glob('*.json'))
        self.assertGreaterEqual(len(packages), 2)
        for path in packages:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unpaid_underpaid_cancelled_disputed_refunded_and_replay_are_rejected(self):
        for scenario in ('unpaid', 'underpaid', 'cancelled', 'disputed', 'refunded', 'replay', 'invalid_session'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                previous, self.path = self.path, Path(directory)
                try:
                    subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                                   capture_output=True, timeout=5, check=True)
                    with provider(scenario) as port:
                        result, data = self.run_order(port)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotEqual(data['state'], 'AWAITING_OWNER_APPROVAL')
                    self.assertFalse(data['owned_fulfillment_started'])
                    self.assertFalse(list(self.path.glob('*.review.json')))
                finally: self.path = previous

    def test_later_refund_blocks_previously_reviewed_order(self):
        with provider() as port:
            self.assertEqual(self.run_order(port)[0].returncode, 0)
        with provider('refunded') as port:
            result, data = self.run_order(port)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['state'], 'HELD')
        with provider() as port:
            self.assertEqual(self.run_order(port)[0].returncode, 2)

    def test_invalid_input_and_unsupported_authorization_flags_are_rejected(self):
        with provider() as port:
            result, data = self.run_order(port, session='customer_source.py')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['provider_requests'], 0)
        probe = subprocess.run(COMMAND + ['run', '--root', str(self.path), '--port', '9999',
                                         '--payment-verified', '/private/customer-secret'],
                               env=ENV, cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(probe.returncode, 2)
        self.assertNotIn('customer-secret', probe.stdout + probe.stderr)

    def test_outage_fails_closed_and_restart_resumes_committed_payment_checkpoint(self):
        with provider() as port:
            interrupted, data = self.run_order(port, '--stop-after', 'payment')
            self.assertEqual(interrupted.returncode, 3)
            self.assertEqual(data['status'], 'interrupted')
        outage, data = self.run_order(port)
        self.assertEqual(outage.returncode, 2)
        self.assertEqual(data['reason'], 'provider_unavailable')
        with provider() as new_port:
            recovered, data = self.run_order(new_port)
        self.assertEqual(recovered.returncode, 0)
        self.assertEqual(data['state'], 'AWAITING_OWNER_APPROVAL')

    def test_killed_worker_recovers_scope_checkpoint_without_duplicate_job(self):
        with provider() as port:
            child = subprocess.Popen(COMMAND + ['run', '--root', str(self.path), '--port', str(port),
                                               '--pause-after-scope'], env=ENV, cwd=ROOT,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
            try:
                child.stdin.write(json.dumps({'session_id': SESSION})); child.stdin.close()
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=5))
                checkpoint = json.loads(child.stdout.readline())
                self.assertEqual(checkpoint['checkpoint'], 'scope')
                child.kill(); child.wait(timeout=3)
            finally:
                if child.poll() is None: child.kill(); child.wait(timeout=3)
                child.stdout.close(); child.stderr.close()
            result, data = self.run_order(port)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(data['owned_job_count'], 1)

    def test_revocation_and_cancellation_are_terminal_durable_holds(self):
        for reason in ('revoked', 'cancelled'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                previous, self.path = self.path, Path(directory)
                try:
                    subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                                   capture_output=True, timeout=5, check=True)
                    with provider() as port:
                        self.assertEqual(self.run_order(port, '--stop-after', 'scope')[0].returncode, 3)
                        held = subprocess.run(COMMAND + ['hold', '--root', str(self.path), '--reason', reason],
                                              env=ENV, cwd=ROOT, capture_output=True, text=True, timeout=5)
                        self.assertEqual(held.returncode, 0)
                        result, data = self.run_order(port)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(data['state'], 'HELD')
                    self.assertEqual(data['provider_requests'], 0)
                    self.assertFalse(list(self.path.glob('*.review.json')))
                finally:
                    self.path = previous

    def test_http_faults_fail_closed_without_following_redirects(self):
        for fault in ('malformed', 'oversized', 'redirect', 'http_error'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                previous, self.path = self.path, Path(directory)
                try:
                    subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                                   capture_output=True, timeout=5, check=True)
                    with provider(fault, fault=True) as port:
                        result, data = self.run_order(port)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(data['provider_requests'], 1)
                    self.assertEqual(data['reason'], 'provider_evidence_rejected')
                    self.assertFalse(data['owned_fulfillment_started'])
                finally:
                    self.path = previous

    def test_refund_between_verification_and_final_review_prevents_package(self):
        with provider('refund_on_final', fault=True) as port:
            result, data = self.run_order(port)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['state'], 'HELD')
        self.assertEqual(data['independent_owned_replays'], 1)
        self.assertFalse(list(self.path.glob('*.review.json')))

    def test_scope_expiring_during_final_provider_read_blocks_review_package(self):
        with provider('expire_on_final', fault=True) as port:
            result, data = self.run_order(port, '--scope-ttl', '1')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['state'], 'HELD')
        self.assertEqual(data['reason'], 'scope_expired')
        self.assertFalse(list(self.path.glob('*.review.json')))

    def test_every_persisted_checkpoint_resumes_after_process_exit(self):
        for checkpoint in ('proposed', 'verified', 'packaged'):
            with self.subTest(checkpoint=checkpoint), tempfile.TemporaryDirectory() as directory:
                previous, self.path = self.path, Path(directory)
                try:
                    subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                                   capture_output=True, timeout=5, check=True)
                    with provider() as port:
                        result, data = self.run_order(port, '--stop-after', checkpoint)
                        self.assertEqual(result.returncode, 3)
                        result, data = self.run_order(port)
                    self.assertEqual(result.returncode, 0)
                    self.assertEqual(data['owned_job_count'], 1)
                    self.assertEqual(data['independent_owned_replays'], int(checkpoint == 'proposed'))
                finally:
                    self.path = previous

    def test_fifo_workspace_marker_fails_closed_without_hanging(self):
        marker = self.path / '.phase8-SIMULATION_ONLY'
        marker.unlink()
        os.mkfifo(marker, mode=0o600)
        try:
            result, data = self.run_order(9999)
        except subprocess.TimeoutExpired:
            self.fail('Workspace FIFO blocked the coordinator')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['provider_requests'], 0)

    def test_delivery_and_customer_execution_commands_do_not_exist(self):
        for command in ('deliver', 'approve', 'execute', 'customer-source'):
            result = subprocess.run(COMMAND + [command], env=ENV, cwd=ROOT,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, 'Synthetic order arguments rejected\n')

    def test_scope_expiry_revocation_and_tampered_packages_never_become_ready(self):
        with provider() as port:
            result, _ = self.run_order(port, '--scope-ttl', '1', '--stop-after', 'scope')
            self.assertEqual(result.returncode, 3)
            time.sleep(1.1)
            self.assertEqual(self.run_order(port)[0].returncode, 2)
        with tempfile.TemporaryDirectory() as directory:
            previous, self.path = self.path, Path(directory)
            try:
                subprocess.run(COMMAND + ['init', '--root', str(self.path)], env=ENV, cwd=ROOT,
                               capture_output=True, check=True, timeout=5)
                with provider() as port:
                    self.assertEqual(self.run_order(port)[0].returncode, 0)
                    package = self.path / 'phase8.SIMULATION_ONLY.review.json'
                    package.write_text(package.read_text()+' ')
                    self.assertEqual(self.run_order(port)[0].returncode, 2)
            finally: self.path = previous


if __name__ == '__main__':
    unittest.main()
