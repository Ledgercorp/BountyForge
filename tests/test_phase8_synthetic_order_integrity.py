"""Admission, durable metadata and owned-ledger integrity on actual SQLite files."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from bountyforge.paid_review_ledger import PaidReviewLedger, ReviewLedgerRejected
from bountyforge.phase7_owned_demo import canonical, digest
from bountyforge.phase8_synthetic_order import (
    DATABASE, JOB, PACKAGE, SimulatorStripeGate, SimulationRejected,
    SyntheticOrder, initialize,
)
from tests.test_phase8_synthetic_order_process import provider


class SyntheticOrderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        initialize(self.root)

    def test_payment_and_scope_are_durable_separate_simulation_evidence(self):
        with provider() as port:
            order = SyntheticOrder(self.root)
            try:
                code, _ = order.run(SimulatorStripeGate(port), stop_after='scope')
                self.assertEqual(code, 3)
                tables = {r[0] for r in order.ledger.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn('simulation_only_evidence', tables)
                rows = order.ledger.db.execute('SELECT kind,record,record_sha256 FROM simulation_only_evidence').fetchall()
            finally:
                order.close()
        records = {kind: json.loads(raw) for kind, raw, sha in rows}
        self.assertEqual(set(records), {'simulated_payment', 'synthetic_scope'})
        for kind, raw, sha in rows:
            self.assertEqual(sha, digest(canonical(json.loads(raw))))
            self.assertIs(records[kind]['real_payment_verified'], False)
            self.assertIs(records[kind]['owner_consent_verified'], False)
        self.assertIs(records['synthetic_scope']['customer_rights_verified'], False)

    def test_simulator_cannot_enter_existing_paid_review_ledger(self):
        with self.assertRaises(ReviewLedgerRejected):
            PaidReviewLedger(object(), SimulatorStripeGate(9999))

    def test_order_rejects_non_simulator_before_invoking_it(self):
        class UnexpectedGate:
            def verify(self, session):
                raise AssertionError('Untrusted transport invoked')
        order = SyntheticOrder(self.root)
        try:
            with self.assertRaisesRegex(SimulationRejected, 'simulator_required'):
                order.run(UnexpectedGate())
        finally:
            order.close()

    def test_tampered_owned_event_is_rejected_before_more_provider_work(self):
        with provider() as port:
            order = SyntheticOrder(self.root)
            try:
                self.assertEqual(order.run(SimulatorStripeGate(port), stop_after='scope')[0], 3)
            finally:
                order.close()
            with sqlite3.connect(self.root / DATABASE) as db:
                db.execute("UPDATE events SET evidence_sha=? WHERE rev=0", ('0'*64,))
            with self.assertRaisesRegex(SimulationRejected, 'ledger_tampered'):
                recovered = SyntheticOrder(self.root)
                recovered.close()

    def test_review_package_binds_simulation_evidence_and_never_claims_consent(self):
        with provider() as port:
            order = SyntheticOrder(self.root)
            try:
                code, outcome = order.run(SimulatorStripeGate(port))
                self.assertEqual(code, 0)
                package = json.loads((self.root / PACKAGE).read_bytes())
                self.assertIs(package.get('simulated_payment_verified'), True)
                self.assertIs(package.get('synthetic_scope_reviewed'), True)
                self.assertEqual(outcome['package_sha256'], digest((self.root / PACKAGE).read_bytes()))
                self.assertIs(package.get('owner_consent_verified'), False)
                self.assertIs(package.get('customer_rights_verified'), False)
                self.assertEqual(len(package.get('synthetic_scope_sha256', '')), 64)
                self.assertEqual(len(package.get('simulated_payment_sha256', '')), 64)
            finally:
                order.close()

    def test_hold_transitions_existing_owned_job_to_held(self):
        with provider() as port:
            order = SyntheticOrder(self.root)
            try:
                self.assertEqual(order.run(SimulatorStripeGate(port), stop_after='scope')[0], 3)
                order.hold('revoked')
                self.assertEqual(order.ledger.read(JOB)['step'], 'HELD')
            finally:
                order.close()

    def test_crash_after_package_binding_recovers_without_another_owned_replay(self):
        with provider() as port:
            order = SyntheticOrder(self.root)
            try:
                code, outcome = order.run(SimulatorStripeGate(port), stop_after='packaged')
                self.assertEqual(code, 3)
                self.assertEqual(outcome['status'], 'interrupted')
            finally:
                order.close()
            recovered = SyntheticOrder(self.root)
            try:
                code, outcome = recovered.run(SimulatorStripeGate(port))
                self.assertEqual(code, 0)
                self.assertEqual(outcome['independent_owned_replays'], 0)
            finally:
                recovered.close()


if __name__ == '__main__':
    unittest.main()
