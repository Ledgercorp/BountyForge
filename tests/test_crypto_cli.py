import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]


class CryptoProcessTests(unittest.TestCase):
    def call(self,*args):
        return subprocess.run([sys.executable,'-m','scripts.crypto_work',*args],cwd=ROOT,text=True,capture_output=True,timeout=15)

    def test_real_process_rehearsal_and_restart_never_become_actual_income(self):
        with tempfile.TemporaryDirectory() as t:
            directory=Path(t)
            for i in range(2):
                out=directory/('result'+str(i)+'.json')
                p=self.call('rehearse','--admit-owned-simulation','--state-dir',str(directory),'--output',str(out))
                self.assertEqual(p.returncode,0,p.stderr);r=json.loads(out.read_text())
                self.assertEqual(r['status'],'PASSED');self.assertEqual(r['real_payments'],0);self.assertEqual(r['real_submissions'],0)
                self.assertEqual(r['earnings']['confirmed_real_earnings_usd'],'0');self.assertEqual(r['earnings']['simulated_received_assets'],{'USDC':'1'})
                self.assertTrue(r['external_submission_refused']);self.assertEqual(r['restarted_existing_state'],bool(i))

    def test_unapproved_live_operations_fail_at_cli_boundary(self):
        for operation in ('register','submit','withdraw','execute-customer'):
            r=self.call(operation);self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)

    def test_discovery_and_rehearsal_require_explicit_safe_scope(self):
        self.assertEqual(self.call('discover').returncode,2)
        self.assertEqual(self.call('rehearse').returncode,2)
        r=self.call('status');self.assertEqual(r.returncode,0)
        self.assertFalse(json.loads(r.stdout)['third_party_execution_authorized'])
