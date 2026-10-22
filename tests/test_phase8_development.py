"""Owned development catalog acceptance; reference fixes are never model results."""
import ast
import hashlib
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from bountyforge.curated_docker import (
    MARKER as HISTORICAL_MARKER, _execute, verify_runtime_boundary,
)
from bountyforge.curated_tasks import TASKS as HISTORICAL_TASKS, editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.statements import stage_statements, statement_catalog

TASKS = Path(__file__).resolve().parents[1] / 'benchmarks/phase8/development_tasks'
MARKER = '.bountyforge-phase8-owned-development'


def load_catalog():
    manifest = json.loads((TASKS / 'manifest.json').read_text())
    if (manifest.get('role') != 'owned_development' or manifest.get('not_heldout') is not True
            or manifest.get('reference_model_generated') is not False
            or len(manifest.get('tasks', [])) != 6):
        raise ValueError('Not the pinned owned development catalog')
    return manifest


def selected_case(task_id):
    matches = [task for task in load_catalog()['tasks'] if task['id'] == task_id]
    if len(matches) != 1 or not re.fullmatch('[a-z_]{3,40}', task_id):
        raise ValueError('Unknown owned development case')
    return matches[0]


def reference_content(task):
    """Trusted DEV_ONLY statement proposals, checked without executing source."""
    original = TASKS / task['id']
    source = (original / task['file']).read_text()
    staged = stage_statements(json.dumps({'changes': task['reference_changes']}),
                              original, task['file'], editable_scope(source, task['symbol']),
                              task['sha256'][task['file']])
    return staged['files'][0]['content']


def verify_owned_copy(root, task_id, *, reference=False):
    """No arbitrary workspace or candidate is admitted, including forged markers."""
    task = selected_case(task_id)
    root = Path(root)
    if root.is_symlink():
        raise ValueError('Symlinked owned development root')
    root = root.resolve(strict=True)
    expected_files = {'subject.py', 'tests/test_regression.py', MARKER}
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            raise ValueError('Unsafe owned development object')
        if path.is_file():
            if path.stat().st_nlink != 1 or path.stat().st_size > 12000:
                raise ValueError('Owned development file outside budget')
            actual.add(path.relative_to(root).as_posix())
    if actual != expected_files or (root / MARKER).read_text() != task_id:
        raise ValueError('Owned development identity mismatch')
    trusted = TASKS / task_id
    for name, digest in task['sha256'].items():
        if hashlib.sha256((trusted / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Owned development catalog hash changed')
    if (root / 'tests/test_regression.py').read_bytes() != (trusted / 'tests/test_regression.py').read_bytes():
        raise ValueError('Owned development acceptance tests changed')
    expected_source = reference_content(task) if reference else (trusted / task['file']).read_text()
    if (root / task['file']).read_text() != expected_source:
        raise ValueError('Not exact baseline or validated development reference')
    return root


def run_owned_fixture(task_id, *, reference=False):
    """Only a fixed case ID and baseline/reference flag reach hardened Docker."""
    task = selected_case(task_id)
    with tempfile.TemporaryDirectory(prefix='bf-phase8-dev-owned-') as directory:
        work = Path(directory) / 'fixture'
        shutil.copytree(TASKS / task_id, work)
        (work / MARKER).write_text(task_id)
        if reference:
            (work / task['file']).write_text(reference_content(task))
        verified = verify_owned_copy(work, task_id, reference=reference)
        result = _execute(verified, None, 12)
        result['passed'] = (result['passed']
                            and re.search(r'Ran [1-9][0-9]* tests?', result['output']) is not None
                            and result['output'].rstrip().endswith('OK'))
        return result


class Phase8DevelopmentCatalogTests(unittest.TestCase):
    def test_six_unique_owned_development_cases_and_exact_catalog_hashes(self):
        manifest = load_catalog()
        self.assertEqual(len({task['id'] for task in manifest['tasks']}), 6)
        for task in manifest['tasks']:
            self.assertEqual(task['file'], 'subject.py')
            self.assertEqual(set(task['sha256']), {'subject.py', 'tests/test_regression.py'})
            root = TASKS / task['id']
            self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()},
                             set(task['sha256']))
            for name, digest in task['sha256'].items():
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)
                ast.parse((root / name).read_text())

    def test_all_reference_fixes_use_unchanged_statement_scope_and_budgets(self):
        for task in load_catalog()['tasks']:
            with self.subTest(task=task['id']):
                source = (TASKS / task['id'] / task['file']).read_text()
                allowed = editable_scope(source, task['symbol'])
                units = statement_catalog(source, allowed)
                self.assertGreaterEqual(len(task['reference_changes']), 1)
                self.assertLessEqual(len(task['reference_changes']), 3)
                for change in task['reference_changes']:
                    self.assertIn(change['line'], units)
                    self.assertLessEqual(change['new'].count('\n'), 2)
                    self.assertLessEqual(len(change['new'].encode()), 400)
                revised = reference_content(task)
                self.assertNotEqual(revised, source)
                self.assertEqual([n.name for n in ast.walk(ast.parse(revised)) if isinstance(n, ast.FunctionDef)],
                                 [n.name for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)])

    def test_catalog_exercises_multiline_units_and_related_statement_changes(self):
        multiline = related = False
        for task in load_catalog()['tasks']:
            source = (TASKS / task['id'] / task['file']).read_text()
            units = statement_catalog(source, editable_scope(source, task['symbol']))
            multiline |= any(units[change['line']]['end_line'] > change['line']
                             for change in task['reference_changes'])
            related |= len(task['reference_changes']) > 1
        self.assertTrue(multiline)
        self.assertTrue(related)

    def test_forged_marker_modified_tests_source_and_symlinks_are_denied(self):
        task = load_catalog()['tasks'][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'fixture'
            shutil.copytree(TASKS / task['id'], root)
            (root / MARKER).write_text(task['id'])
            self.assertEqual(verify_owned_copy(root, task['id']), root.resolve())
            source = (root / 'subject.py').read_text()
            (root / 'subject.py').write_text('raise RuntimeError("not admitted")\n')
            with self.assertRaises(ValueError): verify_owned_copy(root, task['id'])
            (root / 'subject.py').write_text(source)
            tests = (root / 'tests/test_regression.py').read_text()
            (root / 'tests/test_regression.py').write_text('print("OK")\n')
            with self.assertRaises(ValueError): verify_owned_copy(root, task['id'])
            (root / 'tests/test_regression.py').write_text(tests)
            (root / 'external').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError): verify_owned_copy(root, task['id'])

    def test_development_reference_is_not_accepted_as_original_baseline(self):
        task = load_catalog()['tasks'][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'fixture'
            shutil.copytree(TASKS / task['id'], root)
            (root / MARKER).write_text(task['id'])
            (root / task['file']).write_text(reference_content(task))
            with self.assertRaises(ValueError): verify_owned_copy(root, task['id'])
            self.assertEqual(verify_owned_copy(root, task['id'], reference=True), root.resolve())

    def test_unknown_case_and_arbitrary_path_never_select_execution(self):
        for task_id in ('../subject.py', '/etc/passwd', 'heldout', ''):
            with self.subTest(task=task_id), self.assertRaises(ValueError):
                selected_case(task_id)

    @unittest.skipUnless(os.environ.get('BOUNTYFORGE_PHASE8_DEV_DOCKER') == '1',
                         'Explicit owned-development Docker validation not selected')
    def test_docker_reproduces_every_baseline_and_accepts_development_references(self):
        # References are manually authored DEV_ONLY candidates, never model fixes.
        with tempfile.TemporaryDirectory(prefix='bf-phase8-dev-preflight-') as directory:
            baseline = Path(directory) / 'baseline'
            shutil.copytree(HISTORICAL_TASKS / '459', baseline)
            (baseline / HISTORICAL_MARKER).write_text('459')
            proof = verify_runtime_boundary(baseline)
        self.assertTrue(proof['cleanup_verified'])
        results = []
        for task in load_catalog()['tasks']:
            baseline = run_owned_fixture(task['id'])
            self.assertEqual(baseline['returncode'], 1, task['id'])
            self.assertRegex(baseline['output'], r'FAILED \((?:failures|errors)=[1-9]')
            reference = run_owned_fixture(task['id'], reference=True)
            self.assertTrue(reference['passed'], (task['id'], reference['output']))
            results.append({'id': task['id'], 'baseline': baseline, 'development_reference': reference})
        destination = os.environ.get('BOUNTYFORGE_PHASE8_DEV_EVIDENCE')
        if destination:
            Path(destination).write_text(json.dumps({'kind': 'DEV_ONLY_REFERENCE_VALIDATION',
                'model_calls': 0, 'model_generated_repairs': 0, 'heldout_accuracy_measured': False,
                'sandbox_preflight': proof, 'tasks': results}, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
