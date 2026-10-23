"""Pinned owned Phase8 preparation and recorded-candidate replay; no inference.

This module never constructs a provider or admits arbitrary repositories. Financial
authority is unresolved, so no public API here can initiate model requests.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path, PurePosixPath

from bountyforge.curated_docker import IMAGE, _execute, verify_runtime_boundary
from bountyforge.curated_tasks import editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.line_scope import infer_editable_lines
from bountyforge.repair_session import (PROTOCOL, SESSION_SYSTEM, check_receipt,
                                        make_prompt, validate_proposal_bindings)
from bountyforge.statements import stage_statements
from bountyforge.worker import FIXTURE_MARKER

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_MANIFEST = 'benchmarks/phase8/evaluation_tasks/manifest.json'
PRIMARY_SHA256 = '6c01abe0e35fafbb7aee4de108b512ff53c2f9b0150e3191c3c57b04ae771687'
CORE_REVISION = '48ce3f15a134ba06846d7eda8fe4ac2e594e7563'
CORE_SHA256 = {'bountyforge/curated_docker.py': '0beb01183867f514029f466274e641f5e9e2860de7a56d34fe725a12b61dfa2f',
 'bountyforge/curated_tasks.py': '048bf0efe8e44278d4fb5a34ebc951b1d27c7034fb28a77da94f6990b965d48f',
 'bountyforge/drafts.py': 'e5336eb40548b72fae901d6b281ffd0d45de5d2cbf04f0189f2721f700b29af5',
 'bountyforge/line_scope.py': 'df2d83ccc9f290b387df299625c63fe16729a63029cc481c9a05d00adc0f6128',
 'bountyforge/lineedit.py': 'cfafdde8490cd3f7f84e7f3ef3a10aa0bc43973baa3468ec431e7ee4d2205e14',
 'bountyforge/repair_context.py': 'fb0aac6f25e7ad23e7fbedba20d6638c523c5304508bedfcd5b892d419f7b70f',
 'bountyforge/repair_session.py': 'b011ce262e9cba989afb02c69fbd2fd325345d9aaff76349378e7b674c65e8b3',
 'bountyforge/statements.py': '7ee92b1a794ce221042196ac7e5fedd97792691184f3d2709d182787ecfeb460',
 'bountyforge/worker.py': '564678b2c00c750ee580a4bb802d9f5236258b2d7cf24b30da03ebfdf4d655fb',
 'fixtures/controlled/addition/.bountyforge-controlled-fixture': 'df396aaf621fce629c25e37ec29905fc91e4d233fee31a3c65df644e3cbfa74a',
 'fixtures/controlled/addition/README.md': '09a167e797a54c67171424141cdc605f3ff1046fc55ac82a9468ddf91208cea7',
 'fixtures/controlled/addition/calc.py': 'e1a894022d1a082987b87adecb623438c9e386d86b2b621cff4a5fe7fdf7edc8',
 'fixtures/controlled/addition/tests/test_calc.py': '5fa33bfe90c2cd4c3da0fe31421138fc75f718b9341c3a3eb732b078ddc53f48'}
CONTROLS = (
    'network_denied', 'loopback_inference_unreachable', 'source_writes_denied',
    'root_writes_denied', 'secrets_absent', 'uid_unprivileged', 'capabilities_empty',
    'no_new_privileges', 'seccomp_active', 'memory_limit_enforced', 'swap_disabled',
    'cpu_quota_verified', 'pid_limit_verified', 'tmpfs_bounded_noexec',
    'wall_clock_enforced', 'cleanup_verified', 'output_bounded',
    'docker_socket_absent', 'pid_pressure_enforced', 'cpu_pressure_enforced',
)
MAX_REPORT_BYTES = 500_000
CREDENTIAL_NAMES = ('GROQ_API_KEY', 'OPENAI_API_KEY', 'STRIPE_SECRET_KEY', 'GITHUB_TOKEN', 'GH_TOKEN')
SESSION_BOUNDARY_FLAGS = ('customer_execution_authorized', 'delivery_authorized', 'paid_fallback')


class EvaluationRejected(ValueError):
    pass


def require_credential_free_host():
    if any(name in os.environ for name in CREDENTIAL_NAMES):
        raise EvaluationRejected('Preparation and replay refuse inference/payment/publication credentials')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_core():
    if not CORE_SHA256:
        raise EvaluationRejected('Frozen core pins missing')
    for name, expected in CORE_SHA256.items():
        path = ROOT/name
        if path.is_symlink() or digest(path.read_bytes()) != expected:
            raise EvaluationRejected('Frozen core changed')


def _tree(root, expected_files, expected_directories):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise EvaluationRejected('Owned tree root rejected')
    files, directories = set(), set()
    for path in root.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise EvaluationRejected('Unsafe owned filesystem object')
        name = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.add(name)
        else:
            info = path.stat()
            if info.st_nlink != 1 or info.st_size > 12000:
                raise EvaluationRejected('Owned file bounds rejected')
            files.add(name)
    if files != expected_files or directories != expected_directories:
        raise EvaluationRejected('Owned tree differs from exact selection')


class Catalog:
    """An explicit caller-pinned selection; it conveys no financial authority.

    Supplemental catalogs require a selection file and its independently supplied
    digest. Every manifest must stay under benchmarks/phase8 in this repository.
    Pins and selected source trees are rechecked on every admission.
    """
    def __init__(self, selection_file=None, selection_sha256=None):
        if (selection_file is None) != (selection_sha256 is None):
            raise EvaluationRejected('Selection file and exact pin required together')
        self.path = Path(selection_file) if selection_file is not None else None
        self.pin = selection_sha256
        self.novelty = 'Primary catalog novelty audit pending; preparation is not model accuracy.'
        self.selection_sha256 = None

    def tasks(self):
        verify_core()
        if self.path is None:
            config = {'schema': 1, 'novelty': self.novelty, 'manifests': [
                {'path': PRIMARY_MANIFEST, 'sha256': PRIMARY_SHA256, 'case_ids': 'all'}]}
        else:
            if self.path.is_symlink() or self.path.stat().st_nlink != 1:
                raise EvaluationRejected('Unsafe selection file')
            raw = self.path.read_bytes()
            if len(raw) > 20000 or digest(raw) != self.pin:
                raise EvaluationRejected('Trusted selection bytes changed')
            config = json.loads(raw)
        if (not isinstance(config, dict) or set(config) != {'schema', 'novelty', 'manifests'}
                or config['schema'] != 1 or not isinstance(config['novelty'], str)
                or not 1 <= len(config['novelty']) <= 500
                or not isinstance(config['manifests'], list) or not 1 <= len(config['manifests']) <= 4):
            raise EvaluationRejected('Invalid trusted selection')
        self.novelty = config['novelty']
        self.selection_sha256 = self.pin if self.path is not None else digest(json.dumps(config, sort_keys=True).encode())
        selected = []
        for entry in config['manifests']:
            if not isinstance(entry, dict) or set(entry) != {'path', 'sha256', 'case_ids'}:
                raise EvaluationRejected('Invalid selected catalog')
            name = entry['path']
            if (not isinstance(name, str) or PurePosixPath(name).is_absolute()
                    or '..' in PurePosixPath(name).parts or '\\' in name
                    or not name.startswith('benchmarks/phase8/') or not name.endswith('/manifest.json')):
                raise EvaluationRejected('Catalog path outside owned Phase8 tree')
            manifest = ROOT/name
            if any(path.is_symlink() for path in [manifest, *manifest.parents] if path != ROOT.parent):
                raise EvaluationRejected('Symlinked catalog path')
            raw = manifest.read_bytes()
            if len(raw) > 100000 or digest(raw) != entry['sha256']:
                raise EvaluationRejected('Selected manifest pin changed')
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('provenance'), dict):
                raise EvaluationRejected('Owned manifest object required')
            if (data.get('schema') != 1 or data.get('kind') not in (
                    'sealed_owned_python_maintenance_evaluation', 'sealed_owned_python_maintenance_supplement')
                    or data.get('provenance', {}).get('owner') != 'BountyForge / LeftSock Labs'
                    or data.get('provenance', {}).get('license') != 'MIT'
                    or data.get('provenance', {}).get('reference_repairs_supplied') is not False
                    or not isinstance(data.get('tasks'), list)):
                raise EvaluationRejected('Unrecognized owned catalog')
            if (data['kind'].endswith('_supplement')
                    and data['provenance'].get('core_freeze_commit') != CORE_REVISION):
                raise EvaluationRejected('Supplement targets a different frozen core')
            tasks = data['tasks']
            if not all(isinstance(task, dict) and isinstance(task.get('id'), str) for task in tasks):
                raise EvaluationRejected('Owned task identities required')
            if len({task['id'] for task in tasks}) != len(tasks):
                raise EvaluationRejected('Duplicate catalog identity')
            ids = entry['case_ids']
            if ids == 'all':
                ids = [task['id'] for task in tasks]
            if (not isinstance(ids, list) or not ids or not all(isinstance(case_id, str) for case_id in ids)
                    or len(set(ids)) != len(ids)
                    or not set(ids) <= {task['id'] for task in tasks}):
                raise EvaluationRejected('Explicit selected case identities required')
            for case_id in ids:
                task = next(task for task in tasks if task['id'] == case_id)
                if (not isinstance(case_id, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', case_id)
                        or task.get('file') != 'subject.py' or not isinstance(task.get('symbol'), str)
                        or not task['symbol'].isidentifier()
                        or not isinstance(task.get('description'), str)
                        or set(task.get('sha256', {})) != {'subject.py', 'tests/test_regression.py'}):
                    raise EvaluationRejected('Invalid owned task shape')
                root = manifest.parent/case_id
                _tree(root, set(task['sha256']), {'tests'})
                for filename, expected in task['sha256'].items():
                    if not re.fullmatch('[0-9a-f]{64}', expected) or digest((root/filename).read_bytes()) != expected:
                        raise EvaluationRejected('Selected source or tests changed')
                selected.append(dict(copy.deepcopy(task), catalog=name,
                                     catalog_sha256=entry['sha256']))
        if not 1 <= len(selected) <= 80 or len({task['id'] for task in selected}) != len(selected):
            raise EvaluationRejected('Selection count or identities rejected')
        return selected


def original_root(spec):
    return (ROOT/spec['catalog']).parent/spec['id']


def _known(catalog, spec):
    if spec not in catalog.tasks():
        raise EvaluationRejected('Task differs from pinned selection')


def materialize(catalog, spec, root):
    _known(catalog, spec)
    shutil.copytree(original_root(spec), root)
    (Path(root)/FIXTURE_MARKER).write_text('owned-phase8-'+spec['id'])
    admit(catalog, spec, root)
    # Only this exact admitted disposable owned copy is made readable by the
    # unchanged unprivileged Docker UID. Checkout/private source modes stay put.
    root = Path(root)
    for path in (root, *root.rglob('*')):
        path.chmod(0o755 if path.is_dir() else 0o644)
    admit(catalog, spec, root)


def admit(catalog, spec, root, *, candidate=None):
    _known(catalog, spec)
    root = Path(root)
    _tree(root, {'subject.py', 'tests/test_regression.py', FIXTURE_MARKER}, {'tests'})
    if (root/FIXTURE_MARKER).read_text() != 'owned-phase8-'+spec['id']:
        raise EvaluationRejected('Exact owned marker changed')
    for name, expected in spec['sha256'].items():
        if candidate is not None and name == 'subject.py':
            expected = digest(candidate.encode())
        if digest((root/name).read_bytes()) != expected:
            raise EvaluationRejected('Owned bytes differ from admitted provenance')
    return root


def validate_proof(proof):
    if (not isinstance(proof, dict) or not all(proof.get(name) is True for name in CONTROLS)
            or proof.get('image_digest') != IMAGE.split('@')[1]
            or proof.get('untrusted_execution_certified') is not False):
        raise EvaluationRejected('Fresh complete twenty-control proof required')


def preflight():
    verify_core()
    proof = verify_runtime_boundary(ROOT/'fixtures/controlled/addition', synthetic=True)
    validate_proof(proof)
    return proof


def observe(catalog, spec, root, *, candidate=None, before_execute=None):
    admit(catalog, spec, root, candidate=candidate)
    if before_execute is not None:
        before_execute()
    result = _execute(root, None, 12)
    admit(catalog, spec, root, candidate=candidate)
    if result.get('error') or result.get('timeout'):
        raise EvaluationRejected('Owned Docker unavailable or exhausted budget')
    receipt = check_receipt({'passed': result.get('passed'), 'exit_code': result.get('returncode'),
                             'timeout': result.get('timeout'), 'output': result.get('output')})
    receipt['seconds'] = result.get('elapsed_seconds')
    receipt['sandbox'] = 'digest_pinned_docker_no_network_read_only_no_privileges'
    return receipt


def assertion_failure(receipt):
    return (not receipt['passed'] and 'FAIL:' in receipt['output']
            and 'FAILED (failures=' in receipt['output'] and 'errors=' not in receipt['output'])


def issue_for(spec):
    return {'verification': 'unverified_candidate', 'target_symbol': spec['symbol'],
            'description_excerpt': spec['description']}


def context_for(spec, root, baseline):
    source = (root/'subject.py').read_text()
    inferred = infer_editable_lines(root, 'subject.py', baseline['output'])
    scope = sorted(set(inferred) & set(editable_scope(source, spec['symbol'])))
    target = [node for node in ast.parse(source).body
              if isinstance(node, ast.FunctionDef) and node.name == spec['symbol']]
    if len(target) != 1 or not scope or any(not target[0].lineno < n <= target[0].end_lineno for n in inferred):
        raise EvaluationRejected('Deterministic localization rejected')
    contract = (root/'tests/test_regression.py').read_text()
    prompt = make_prompt(source, 'subject.py', scope, issue_for(spec), contract,
                         baseline['output'], baseline['output'], '', '')
    return scope, prompt


def _report(mode):
    return {'schema': 1, 'mode': mode, 'status': 'blocked', 'accuracy': None,
            'inference_calls': 0, 'inference_seconds': 0, 'baseline_invocations': 0,
            'baseline_receipts': 0, 'baseline_assertion_failures': 0,
            'cases': [], 'core_revision': CORE_REVISION,
            'core_sha256': dict(CORE_SHA256), 'image': IMAGE,
            'financial_authority': 'unverified; no live inference API enabled',
            'customer_execution_authorized': False, 'delivery_authorized': False,
            'paid_fallback': False}


def prepare(*, selection_file=None, selection_sha256=None, report_path=None):
    """Observe each selected original once after fresh fixed Docker controls."""
    report = _report('prepare'); started = time.monotonic()
    def checkpoint():
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        if report_path is not None:
            write_report(report_path, report)
    def dispatch():
        report['baseline_invocations'] += 1
        checkpoint()
    try:
        require_credential_free_host()
        catalog = Catalog(selection_file, selection_sha256); tasks = catalog.tasks()
        report.update(novelty=catalog.novelty, selection_sha256=catalog.selection_sha256,
                      selected_cases=[task['id'] for task in tasks])
        report['preflight'] = preflight()
        report['status'] = 'preparing'
        checkpoint()
        runner_available = True
        for spec in tasks:
            case = {'case_id': spec['id'], 'status': 'blocked', 'reason': None,
                    'source_sha256': spec['sha256']['subject.py'],
                    'tests_sha256': spec['sha256']['tests/test_regression.py'],
                    'catalog': spec['catalog'],
                    'catalog_sha256': spec['catalog_sha256']}
            report['cases'].append(case)
            if not runner_available:
                case['reason'] = 'runner_disabled_after_failure'
                checkpoint()
                continue
            case['status'] = 'baseline_pending'
            checkpoint()
            try:
                with tempfile.TemporaryDirectory(prefix='bf-phase8-prepare-') as directory:
                    root = Path(directory)/'original'; materialize(catalog, spec, root)
                    baseline = observe(catalog, spec, root, before_execute=dispatch)
                    report['baseline_receipts'] += 1
                    case['status'] = 'blocked'
                    case['baseline'] = baseline
                    if not assertion_failure(baseline):
                        case['reason'] = 'baseline_not_assertion_failure'; continue
                    report['baseline_assertion_failures'] += 1
                    try:
                        scope, prompt = context_for(spec, root, baseline)
                    except (DraftRejected, ValueError, TypeError, SyntaxError):
                        case['reason'] = 'context_rejected'; continue
                    case.update(status='prepared', editable_lines=scope,
                                prompt_sha256=digest(prompt.encode()), prompt_bytes=len(prompt.encode()),
                                prompt=json.loads(prompt))
            except (OSError, RuntimeError, ValueError, TypeError, KeyError):
                case.update(status='blocked', reason='owned_baseline_or_custody_unavailable')
                runner_available = False
                report['runner_disabled_after_failure'] = True
            finally:
                checkpoint()
        report['prepared_cases'] = sum(case['status'] == 'prepared' for case in report['cases'])
        report['status'] = ('prepared' if report['prepared_cases'] == len(tasks)
                            else 'partially_prepared' if report['prepared_cases'] else 'blocked')
    except (OSError, RuntimeError, ValueError, TypeError, KeyError):
        report['reason'] = 'catalog_core_or_preflight_rejected'
    finally:
        checkpoint()
    return report


def _replay_binding(catalog, spec, root, session):
    """Validate recorded candidate provenance; never certify provider origin."""
    if (not isinstance(session, dict) or session.get('protocol') != PROTOCOL
            or session.get('status') != 'review_ready'
            or any(session.get(flag) is not False for flag in SESSION_BOUNDARY_FLAGS)
            or session.get('source_sha256') != spec['sha256']['subject.py']
            or session.get('tests_sha256') != spec['sha256']['tests/test_regression.py']):
        raise EvaluationRejected('Recorded session lacks pinned ready provenance')
    baseline = check_receipt(session['baseline'])
    if not assertion_failure(baseline):
        raise EvaluationRejected('Recorded baseline is not an assertion failure')
    scope, _ = context_for(spec, root, baseline)
    if session.get('editable_lines') != scope:
        raise EvaluationRejected('Recorded scope differs from deterministic scope')
    calls = session.get('calls')
    if not isinstance(calls, list) or not 1 <= len(calls) <= 2 or session.get('model_calls') != len(calls):
        raise EvaluationRejected('Recorded call count rejected')
    source = (root/'subject.py').read_text(); contract = (root/'tests/test_regression.py').read_text()
    previous = ''; latest = baseline['output']
    worker = session.get('worker')
    if not isinstance(worker, dict) or worker.get('status') != 'review_ready':
        raise EvaluationRejected('Recorded worker did not produce a ready candidate')
    attempts = worker.get('attempts')
    if (not isinstance(attempts, list) or len(attempts) != len(calls)
            or not all(isinstance(attempt, dict) for attempt in attempts)):
        raise EvaluationRejected('Recorded worker attempts lack actual call correspondence')
    if (worker.get('patch') != session.get('patch')
            or not check_receipt(worker['independent_verification'])['passed']
            or attempts[-1].get('status') != 'passed'
            or not check_receipt(attempts[-1]['test'])['passed']):
        raise EvaluationRejected('Recorded ready claim contradicts its verification')
    for index, call in enumerate(calls):
        if not isinstance(call, dict):
            raise EvaluationRejected('Recorded actual call must be an object')
        response = call.get('response')
        if (call.get('number') != index+1 or call.get('system') != SESSION_SYSTEM
                or call.get('max_tokens') != 150 or not isinstance(response, str)
                or call.get('response_sha256') != digest(response.encode())
                or call.get('previous_response_sha256') != (digest(previous.encode()) if previous else None)):
            raise EvaluationRejected('Recorded actual transcript binding failed')
        data = json.loads(call['prompt'])
        if not isinstance(data, dict) or not isinstance(data.get('previous_error'), str):
            raise EvaluationRejected('Recorded prompt fields rejected')
        error = data.get('previous_error', '')
        if index == 0 and error:
            raise EvaluationRejected('Initial recorded context includes retry evidence')
        expected = make_prompt(source, 'subject.py', scope, issue_for(spec), contract,
                               baseline['output'], latest, previous, error)
        if call['prompt'] != expected:
            raise EvaluationRejected('Actual prompt differs from pinned source and contract')
        previous = response
        if 'test' in attempts[index]:
            latest = check_receipt(attempts[index]['test'])['output']
    validate_proposal_bindings(source, scope, previous)
    candidate = stage_statements(previous, root, 'subject.py', scope,
                                 spec['sha256']['subject.py'])['files'][0]
    if (session.get('patch') != [{'path': 'subject.py', 'diff': candidate['diff']}]
            or session.get('candidate_sha256') != digest(candidate['content'].encode())):
        raise EvaluationRejected('Recorded patch differs from exact raw response replay')
    return candidate


def replay(record, *, selection_file=None, selection_sha256=None):
    """Fresh credential-free Docker replay of one bound recorded candidate.

    A passing replay is candidate evidence, never a live model accuracy score.
    """
    report = _report('recorded_candidate_replay'); started = time.monotonic()
    try:
        require_credential_free_host()
        if not isinstance(record, dict) or set(record) != {'case_id', 'session'}:
            raise EvaluationRejected('Explicit recorded case and session required')
        if len(json.dumps(record, allow_nan=False).encode()) > MAX_REPORT_BYTES:
            raise EvaluationRejected('Recorded evidence exceeds bounded size')
        catalog = Catalog(selection_file, selection_sha256); tasks = catalog.tasks()
        spec = next(task for task in tasks if task['id'] == record.get('case_id'))
        report.update(case_id=spec['id'], novelty=catalog.novelty,
                      selection_sha256=catalog.selection_sha256)
        with tempfile.TemporaryDirectory(prefix='bf-phase8-replay-') as directory:
            root = Path(directory)/'candidate'; materialize(catalog, spec, root)
            candidate = _replay_binding(catalog, spec, root, record.get('session'))
            (root/'subject.py').write_text(candidate['content'])
            admit(catalog, spec, root, candidate=candidate['content'])
            report['preflight'] = preflight()
            report['verification'] = observe(catalog, spec, root, candidate=candidate['content'])
            report['status'] = 'replay_passed' if report['verification']['passed'] else 'replay_failed'
            report['candidate_sha256'] = digest(candidate['content'].encode())
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, StopIteration):
        report['reason'] = 'recorded_binding_or_fresh_docker_rejected'
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
    return report


def write_report(path, report):
    raw = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False).encode()+b'\n'
    if len(raw) > MAX_REPORT_BYTES:
        raise EvaluationRejected('Evidence report exceeds bounded size')
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(raw); temporary.replace(path)
