import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class EngineCliTests(unittest.TestCase):
    def invoke(self,*args,input=''):
        self.assertIsNotNone(importlib.util.find_spec('scripts.repair_engine'),
                             'The owner engine selector CLI is missing')
        p=subprocess.run([sys.executable,'-m','scripts.repair_engine',*args],cwd=ROOT,
                         input=input,text=True,capture_output=True,timeout=10)
        self.assertNotIn('Traceback',p.stderr)
        return p

    def test_lists_real_choices_and_development_tasks(self):
        p=self.invoke('--list')
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout)
        self.assertEqual([x['label'] for x in data['engines']],['Autonomous Qwen','Codex Agent'])
        self.assertEqual(len(data['tasks']),6)

    def test_codex_configuration_requires_session_instead_of_launching_model(self):
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/'mode.json'
            config.write_text(json.dumps({'engine':'CODEX_AGENT','case_id':'weighted-mix'}))
            p=self.invoke('--config',str(config))
        self.assertEqual(p.returncode,2,p.stderr)
        data=json.loads(p.stdout)
        self.assertEqual(data['engine'],'CODEX_AGENT')
        self.assertEqual(data['outcome'],'CODEX_SESSION_REQUIRED')
        self.assertEqual(data['additional_model_calls'],0)

    def test_real_owner_menu_selection_controls_the_engine(self):
        p=self.invoke('--interactive',input='2\nweighted-mix\n')
        self.assertEqual(p.returncode,2)
        self.assertIn('Autonomous Qwen',p.stderr)
        self.assertIn('Codex Agent',p.stderr)
        self.assertEqual(json.loads(p.stdout)['engine'],'CODEX_AGENT')

    def test_unknown_provider_and_config_authorization_flags_are_rejected(self):
        p=self.invoke('--engine','PAID_API','--case-id','weighted-mix')
        self.assertEqual(p.returncode,2)
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/'mode.json'
            config.write_text('{"engine":"CODEX_AGENT","case_id":"weighted-mix","execute_customer":true}')
            p=self.invoke('--config',str(config))
        self.assertEqual(p.returncode,2)

if __name__=='__main__':unittest.main()
