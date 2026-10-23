"""Static integrity checks only: never import or execute evaluation subjects."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'benchmarks/phase8/evaluation_tasks'
MANIFEST_SHA256 = '6c01abe0e35fafbb7aee4de108b512ff53c2f9b0150e3191c3c57b04ae771687'


class Phase8CatalogTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'manifest.json').is_file(), 'Sealed Phase8 catalog manifest is missing')
        raw = (ROOT/'manifest.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), MANIFEST_SHA256)
        self.manifest = json.loads(raw)

    def test_twenty_distinct_owned_pinned_cases_and_split(self):
        self.assertEqual(self.manifest['schema'], 1)
        self.assertEqual(self.manifest['kind'], 'sealed_owned_python_maintenance_evaluation')
        self.assertEqual(self.manifest['split'], 'held_out_until_phase8_session_freeze')
        tasks = self.manifest['tasks']
        self.assertGreaterEqual(len(tasks), 20)
        self.assertEqual(len({task['id'] for task in tasks}), len(tasks))
        self.assertGreaterEqual(len({task['category'] for task in tasks}), 10)
        self.assertGreaterEqual(len({task['complexity'] for task in tasks}), 6)
        self.assertEqual(self.manifest['provenance']['owner'], 'BountyForge / LeftSock Labs')
        self.assertEqual(self.manifest['provenance']['license'], 'MIT')
        self.assertEqual(self.manifest['provenance']['base_revision'],
                         '7bcbf5e3d7998bad965c2f00ff5756d0076ba0dc')
        self.assertFalse(self.manifest['provenance']['reference_repairs_supplied'])
        self.assertEqual(self.manifest['provenance']['target_execution'], 'not_executed_before_admission')
        self.assertEqual({path.name for path in ROOT.iterdir() if path.is_dir()},
                         {task['id'] for task in tasks})
        for task in tasks:
            self.assertTrue(task['symbol'].isidentifier())
            self.assertTrue(task['id'].isidentifier())
            self.assertEqual(task['baseline_intent'], 'assertion_failure_not_executed')
            self.assertIn('Original owned fixture', task['provenance'])
        old = set()
        for filename in ('phase5/tasks/manifest.json', 'phase5/structural_tasks/manifest.json',
                         'phase6/evaluation_tasks/manifest.json'):
            old.update(task['id'] for task in json.loads((ROOT.parents[1]/filename).read_text())['tasks'])
        self.assertFalse(old.intersection(task['id'] for task in tasks))

    def test_exact_file_hashes_and_small_original_trees(self):
        for task in self.manifest['tasks']:
            with self.subTest(case=task['id']):
                root = ROOT/task['id']
                self.assertFalse(root.is_symlink())
                self.assertFalse((root/'tests').is_symlink())
                self.assertEqual(task['file'], 'subject.py')
                self.assertEqual(set(task['sha256']), {'subject.py', 'tests/test_regression.py'})
                actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
                self.assertEqual(actual, set(task['sha256']))
                for name, expected in task['sha256'].items():
                    path = root/name
                    self.assertFalse(path.is_symlink())
                    self.assertEqual(path.stat().st_nlink, 1)
                    raw = path.read_bytes()
                    self.assertLessEqual(len(raw), 12000)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
                    ast.parse(raw, filename=str(path))

    def test_unique_top_level_target_and_bounded_direct_scope(self):
        multiline = 0
        for task in self.manifest['tasks']:
            tree = ast.parse((ROOT/task['id']/task['file']).read_text())
            functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            self.assertEqual([f.name for f in functions], [task['symbol']])
            self.assertIn(functions[0], tree.body)
            self.assertLessEqual(functions[0].end_lineno-functions[0].lineno, 30)
            self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)))
            multiline += any(isinstance(n, (ast.Assign, ast.Return)) and n.end_lineno > n.lineno
                             for n in ast.walk(tree))
        self.assertGreaterEqual(multiline, 4)

    def test_six_to_eight_direct_target_contract_methods_per_case(self):
        for task in self.manifest['tasks']:
            tree = ast.parse((ROOT/task['id']/'tests/test_regression.py').read_text())
            methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
            imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            self.assertEqual(len(imports), 2)
            self.assertIsInstance(imports[0], ast.Import)
            self.assertEqual([alias.name for alias in imports[0].names], ['unittest'])
            self.assertIsInstance(imports[1], ast.ImportFrom)
            self.assertEqual(imports[1].module, 'subject')
            self.assertEqual([alias.name for alias in imports[1].names], [task['symbol']])
            classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
            self.assertEqual(len(classes), 1)
            self.assertEqual(ast.unparse(classes[0].bases[0]), 'unittest.TestCase')
            self.assertGreaterEqual(len(methods), 6)
            self.assertLessEqual(len(methods), 8)
            self.assertEqual(len({method.name for method in methods}), len(methods))
            for method in methods:
                self.assertTrue(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                    and n.func.id == task['symbol'] for n in ast.walk(method)),
                                task['id']+': failing test must directly identify the source target')


if __name__ == '__main__': unittest.main()
