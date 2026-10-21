"""Nonexecuting identity and shape checks for the independently authored catalog."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'benchmarks/phase6/evaluation_tasks'


class EvaluationCatalogTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'manifest.json').read_text())

    def test_four_unique_owned_cases_with_exact_pinned_files(self):
        self.assertEqual(self.manifest['kind'], 'independently_authored_owned_maintenance_evaluation')
        self.assertEqual(self.manifest['split'], 'held_out_until_repair_implementation_freeze')
        tasks = self.manifest['tasks']
        self.assertEqual(len(tasks), 4)
        self.assertEqual(len({t['id'] for t in tasks}), 4)
        self.assertFalse(self.manifest['provenance']['manual_solution_supplied'])
        for task in tasks:
            with self.subTest(task=task['id']):
                self.assertEqual(task['file'], 'subject.py')
                self.assertEqual(set(task['sha256']), {'subject.py', 'tests/test_regression.py'})
                actual = {p.relative_to(ROOT / task['id']).as_posix()
                          for p in (ROOT / task['id']).rglob('*') if p.is_file()}
                self.assertEqual(actual, set(task['sha256']))
                for path, digest in task['sha256'].items():
                    raw = (ROOT / task['id'] / path).read_bytes()
                    self.assertLess(len(raw), 12000)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_each_source_has_exactly_one_target_and_no_external_imports(self):
        multiline = 0
        for task in self.manifest['tasks']:
            tree = ast.parse((ROOT / task['id'] / task['file']).read_text())
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            self.assertEqual([f.name for f in functions], [task['symbol']])
            self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)))
            multiline += any(isinstance(n, (ast.Assign, ast.Return)) and n.end_lineno > n.lineno
                             for n in ast.walk(tree))
        self.assertGreaterEqual(multiline, 2)

    def test_acceptance_methods_are_nonempty_and_reference_the_exact_target(self):
        for task in self.manifest['tasks']:
            tree = ast.parse((ROOT / task['id'] / 'tests/test_regression.py').read_text())
            methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
            self.assertGreaterEqual(len(methods), 6)
            self.assertTrue(all(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                    and n.func.id == task['symbol'] for n in ast.walk(method))
                                for method in methods))


if __name__ == '__main__':
    unittest.main()
