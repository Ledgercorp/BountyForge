import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def test_read_only_discovery_merges_sources_without_authorizing_candidates(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from datetime import datetime, timezone
        from bountyforge.crypto_opportunities import normalize_github, normalize_superteam
        import scripts.crypto_work as work
        observed=datetime.now(timezone.utc).isoformat()
        feed=normalize_superteam({'id':'agent-listing','slug':'agent-listing','title':'Python maintenance',
            'rewardAmount':'10','token':'USDC','skills':['Python'],'status':'OPEN'},observed)
        github=normalize_github({'html_url':'https://github.com/example/repo/issues/7','title':'Python bug bounty $20',
            'body':'Advertised only; funding unverified.','state':'open','labels':[]},observed)
        algora=normalize_github({'html_url':'https://github.com/example/other/issues/8','title':'Reward: $5',
            'body':'Lead only.','state':'open','labels':[]},observed)

        class Sources:
            def __init__(self,token=None):
                self.token=token
            def discover(self):
                return {'status':'BLOCKED_AUTHENTICATION','opportunities':None,'complete_scan':False}
            def discover_github(self,*,algora_bot=False,language='python'):
                if language!='python':
                    return {'status':'OBSERVED','opportunities':[],'complete_scan':False,'authenticated':False}
                return {'status':'OBSERVED','opportunities':[algora if algora_bot else github],
                    'complete_scan':False,'authenticated':False}
            def market_quote(self,asset):
                return {'asset':asset,'status':'HTTP_ERROR','usd_price':None,'observed_at':observed,
                    'owner_withdrawal_route_verified':False,'guaranteed_liquidity':False}

        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'discovery.json'
            stdout=StringIO()
            with patch.object(work,'CryptoReadOnly',Sources), redirect_stdout(stdout):
                code=work.main(['discover','--admit-public-reads','--output',str(output)])
            self.assertEqual(code,0)
            result=json.loads(output.read_text())
        self.assertEqual(result['source_summary']['github_candidates'],1)
        self.assertEqual(result['source_summary']['algora_bot_comment_candidates'],1)
        self.assertEqual(result['source_summary']['superteam_candidates'],0)
        self.assertFalse(result['complete_scan'])
        self.assertEqual(len(result['opportunities']),2)
        records=[record for group in result['opportunities'] for record in group['records']]
        self.assertTrue(all(x['qualification']['execution_authorized'] is False for x in records))
        self.assertTrue(all(x['qualification']['submission_authorized'] is False for x in records))
        self.assertEqual(result['paid_requests'],0)
        self.assertEqual(result['external_writes'],0)

    def test_superteam_key_file_is_only_consumed_by_trusted_read_client(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from datetime import datetime, timezone
        from bountyforge.crypto_opportunities import normalize_github
        import scripts.crypto_work as work
        token='agent_mock_123456789012345678901234'
        observed=datetime.now(timezone.utc).isoformat()
        lead=normalize_github({'html_url':'https://github.com/example/repo/issues/7','title':'Python bug bounty $20',
            'body':'Advertised only; funding unverified.','state':'open','labels':[]},observed,language_hint='python')
        class Sources:
            def __init__(self,token=None):self.token=token
            def discover(self):return {'status':'BLOCKED_AUTHENTICATION','opportunities':None,'complete_scan':False}
            def discover_github(self,*,algora_bot=False,language='python'):
                return {'status':'OBSERVED','opportunities':[lead] if language=='python' and not algora_bot else [],
                    'complete_scan':False,'authenticated':False}
            def market_quote(self,asset):return {'asset':asset,'status':'HTTP_ERROR','usd_price':None,
                'observed_at':observed,'owner_withdrawal_route_verified':False,'guaranteed_liquidity':False}
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'private-discovery.json';credential_path=Path(directory)/'key'
            out=StringIO()
            with patch.object(work,'load_superteam_api_key',return_value=token) as load, \
                 patch.object(work,'CryptoReadOnly',Sources), redirect_stdout(out):
                code=work.main(['discover','--admit-public-reads','--superteam-key-file',str(credential_path),
                    '--output',str(output)])
            self.assertEqual(code,0);load.assert_called_once_with(credential_path)
            text=output.read_text()+out.getvalue()
            self.assertNotIn(token,text)
            result=json.loads(output.read_text())
            self.assertTrue(result['source_summary']['superteam_credential_configured'])
            self.assertFalse(result['source_summary']['superteam_authenticated'])
