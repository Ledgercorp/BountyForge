import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def module(self):
        try:import phase22_repair as m
        except ImportError:self.fail('DeepSeek owned repair integration is missing')
        return m

    def test_catalog_is_new_owned_pinned_material_and_cannot_pick_arbitrary_paths(self):
        m=self.module();specs=m.catalog().tasks()
        self.assertEqual(len(specs),6)
        with self.assertRaises(ValueError):m.selected_case('../../etc/passwd')
        self.assertEqual(m.selected_case('retry_state')['symbol'],'after_failure')
        from bountyforge.repair_engines import catalog
        self.assertTrue(set(s['id'] for s in specs).isdisjoint(s['id'] for s in catalog(include_quality=True)))

    def test_model_context_contains_no_test_source_or_reference_material(self):
        m=self.module();spec=m.selected_case('retry_state')
        source=(ROOT/'benchmarks/phase8/phase22_development/retry_state/subject.py').read_text()
        task={'description':spec['description'],'source':source,'target_symbol':spec['symbol'],
              'edit_units':[{'line':10,'end_line':10,'kind':'statement','bindings':['exhausted']}],
              'baseline_feedback':{'failing_tests':['test_exact_limit'],'assertions':['False != True']}}
        prompt=m.messages(task,None)
        self.assertIn(source,json.loads(prompt[1]['content'])['source'])
        self.assertNotIn('def test_',str(prompt));self.assertNotIn('reference_patch',str(prompt))
        self.assertIn('test_exact_limit',str(prompt))

    def test_missing_spend_authorization_is_a_process_boundary_refusal(self):
        self.module()
        process=subprocess.run([sys.executable,'-m','phase22_run','run','--plan-sha256','a'*64],
                               cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(process.returncode,2)
        self.assertNotIn('Traceback',process.stderr+process.stdout)
        self.assertIn('authorization',process.stderr)

    def test_unknown_operation_cannot_execute_customer_or_touch_state(self):
        self.module()
        process=subprocess.run([sys.executable,'-m','phase22_run','--execute-customer'],
                               cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(process.returncode,2)
        self.assertNotIn('Traceback',process.stderr+process.stdout)
