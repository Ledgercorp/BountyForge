"""Static catalog and semantic-audit checks; never execute fixture code."""
import ast
import hashlib
import json
from pathlib import Path
import unittest


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / 'benchmarks/phase8/supplemental_tasks'
MANIFEST_SHA256 = 'f34b48d3f1d310188e4efc3b5e35a48d1ed53a883b3e27cfbe8f2aae62a7a851'
SELECTION_SHA256 = '55e7de2b2c59eaaea75a494315df5b95cea5eeabcaeb835309a517f43abb891e'
ORIGINAL_SHA256 = '6c01abe0e35fafbb7aee4de108b512ff53c2f9b0150e3191c3c57b04ae771687'


class SupplementalCatalogTests(unittest.TestCase):
    def setUp(self):
        raw = (ROOT / 'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), MANIFEST_SHA256)
        self.manifest = json.loads(raw)

    def test_frozen_original_preserved_and_semantic_exclusions_explicit(self):
        original = BASE / 'benchmarks/phase8/evaluation_tasks'
        raw = (original / 'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ORIGINAL_SHA256)
        frozen = json.loads(raw)
        for task in frozen['tasks']:
            for name, digest in task['sha256'].items():
                self.assertEqual(hashlib.sha256((original / task['id'] / name).read_bytes()).hexdigest(), digest)
        audit_raw = (ROOT / 'novelty_review.json').read_bytes()
        self.assertEqual(hashlib.sha256(audit_raw).hexdigest(), self.manifest['novelty_review_sha256'])
        audit = json.loads(audit_raw)
        self.assertEqual({entry['id'] for entry in audit['original_case_review']},
                         {task['id'] for task in frozen['tasks']})
        excluded = {entry['id'] for entry in audit['original_case_review']
                    if entry['decision'] == 'exclude_semantic_duplicate'}
        self.assertEqual(excluded, {'middle_observation', 'weighted_measurement'})
        self.assertEqual(len(audit['conservative_additional_exclusions']), 4)
        self.assertEqual(audit['unexposed_problem_count_after_supplement'], 24)
        self.assertEqual(audit['conservative_problem_count_after_supplement'], 20)
        self.assertIn('benchmarks/phase8/development_tasks', audit['comparison_catalogs'])
        self.assertEqual(audit['core_freeze_commit'], '48ce3f15a134ba06846d7eda8fe4ac2e594e7563')

    def test_conservative_selection_pins_exact_twenty_cases(self):
        raw = (ROOT / 'selection.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SELECTION_SHA256)
        selection = json.loads(raw)
        self.assertEqual(selection['schema'], 1)
        self.assertTrue(selection['novelty'])
        groups = selection['manifests']
        self.assertEqual([group['path'] for group in groups],
                         ['benchmarks/phase8/evaluation_tasks/manifest.json',
                          'benchmarks/phase8/supplemental_tasks/manifest.json'])
        self.assertEqual([group['sha256'] for group in groups], [ORIGINAL_SHA256, MANIFEST_SHA256])
        self.assertEqual([len(group['case_ids']) for group in groups], [14, 6])
        original = json.loads((BASE / groups[0]['path']).read_text())
        excluded = {'middle_observation', 'weighted_measurement', 'query_accumulation',
                    'clock_normalization', 'redacted_mapping', 'encounter_unique'}
        self.assertEqual(set(groups[0]['case_ids']), {task['id'] for task in original['tasks']} - excluded)
        self.assertEqual(set(groups[1]['case_ids']), {task['id'] for task in self.manifest['tasks']})
        all_ids = [case_id for group in groups for case_id in group['case_ids']]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_six_new_owned_cases_with_pinned_small_files(self):
        self.assertEqual(self.manifest['kind'], 'sealed_owned_python_maintenance_supplement')
        self.assertFalse(self.manifest['provenance']['reference_repairs_supplied'])
        self.assertEqual(self.manifest['provenance']['target_execution'], 'not_executed_before_admission')
        tasks = self.manifest['tasks']
        self.assertEqual(len(tasks), 6)
        self.assertEqual(len({task['id'] for task in tasks}), 6)
        self.assertEqual(len({task['category'] for task in tasks}), 6)
        self.assertGreaterEqual(len({task['complexity'] for task in tasks}), 3)
        self.assertEqual({path.name for path in ROOT.iterdir() if path.is_dir()}, {task['id'] for task in tasks})
        old_ids = {task['id'] for task in json.loads((BASE / 'benchmarks/phase8/evaluation_tasks/manifest.json').read_text())['tasks']}
        for task in tasks:
            self.assertNotIn(task['id'], old_ids)
            self.assertTrue(task['id'].isidentifier())
            self.assertTrue(task['symbol'].isidentifier())
            case = ROOT / task['id']
            self.assertFalse(case.is_symlink())
            self.assertFalse((case / 'tests').is_symlink())
            self.assertEqual(task['file'], 'subject.py')
            self.assertEqual(set(task['sha256']), {'subject.py', 'tests/test_regression.py'})
            self.assertEqual({path.relative_to(case).as_posix() for path in case.rglob('*') if path.is_file()},
                             set(task['sha256']))
            for name, digest in task['sha256'].items():
                path = case / name
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_nlink, 1)
                raw = path.read_bytes()
                self.assertLessEqual(len(raw), 12000)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                ast.parse(raw, filename=str(path))

    def test_unique_bounded_target_and_direct_unittest_contracts(self):
        for task in self.manifest['tasks']:
            with self.subTest(case=task['id']):
                source = ast.parse((ROOT / task['id'] / 'subject.py').read_text())
                functions = [node for node in ast.walk(source) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
                self.assertEqual([node.name for node in functions], [task['symbol']])
                self.assertIn(functions[0], source.body)
                self.assertLessEqual(functions[0].end_lineno - functions[0].lineno, 30)
                self.assertFalse(any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(source)))
                tests = ast.parse((ROOT / task['id'] / 'tests/test_regression.py').read_text())
                imports = [node for node in ast.walk(tests) if isinstance(node, (ast.Import, ast.ImportFrom))]
                self.assertEqual([ast.unparse(node) for node in imports],
                                 ['import unittest', 'from subject import ' + task['symbol']])
                methods = [node for node in ast.walk(tests) if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')]
                self.assertGreaterEqual(len(methods), 6)
                self.assertLessEqual(len(methods), 8)
                self.assertEqual(len({method.name for method in methods}), len(methods))
                for method in methods:
                    self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                                        and node.func.id == task['symbol'] for node in ast.walk(method)))


if __name__ == '__main__':
    unittest.main()
