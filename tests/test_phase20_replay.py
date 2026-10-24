import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RecordedNativeAcceptanceTests(unittest.TestCase):
    def test_default_off_replay_and_simulation_cannot_execute(self):
        from phase20_replay import replay
        from phase20_protocol_acceptance import run
        with self.assertRaisesRegex(ValueError,'EXPLICIT_RECORDED'):replay()
        with self.assertRaisesRegex(ValueError,'EXPLICIT_PROTOCOL'):run()

    def test_modified_origin_is_rejected_before_verification(self):
        from phase20_replay import ROOT,ORIGINS,validate_origin
        for filename in ORIGINS:
            original=json.loads((ROOT/'evidence/phase20'/filename).read_text())
            case,call,receipt=validate_origin(filename,original)
            changed=copy.deepcopy(original);changed['additional_spending_usd']=1
            with self.assertRaisesRegex(ValueError,'ORIGIN_REJECTED'):validate_origin(filename,changed)
            self.assertIn(receipt['outcome'],('VERIFIED','TEST_FAILED'))

    def test_actual_cli_rejects_execution_and_arbitrary_arguments_without_output(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'unauthorized-output.json'
            for module,extra in (('phase20_replay',[]),('phase20_protocol_acceptance',['--wheel-directory',temp])):
                for forbidden in ([],['--execute-customer']):
                    result=subprocess.run([sys.executable,'-B','-m',module,'--output',str(target),*extra,*forbidden],
                        cwd=root,capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,2)
                    self.assertFalse(target.exists())
