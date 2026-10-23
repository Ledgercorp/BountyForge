"""Owned-only dual-engine orchestration using the existing validators and Docker.

CODEX_AGENT accepts session-authored proposals; it never starts another agent.
No public API accepts source trees, test code, commands, endpoints or file paths.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tarfile
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

from bountyforge.curated_docker import IMAGE, _execute
from bountyforge.curated_tasks import editable_scope
from bountyforge.drafts import DraftRejected
from bountyforge.line_scope import infer_editable_lines
from bountyforge.model import _NoRedirect
from bountyforge.native_qwen import NativeStatementModel as LocalModel
from bountyforge.repair_intelligence import (failure_feedback, source_context, model_prompt,
    revision_proposal, validate_local_dependencies)
from bountyforge.phase8_evaluation import CONTROLS, preflight, validate_proof, verify_core
from bountyforge.repair_session import admit, check_receipt, validate_proposal_bindings
from bountyforge.statements import SYSTEM, stage_statements, statement_catalog
from bountyforge.worker import FIXTURE_MARKER

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'fixtures/phase12'
MANIFEST_SHA256 = '4220ab13e3aae1e8cc688902795eae9a8e809c8a635a0838a6f9e52c4639729d'
DEVELOPMENT = ROOT / 'fixtures/phase13'
DEVELOPMENT_SHA256 = '10a90ac0108d9269cd077f002a5212a1c9a39b7925db145eb367bb672900ef77'
MAINTENANCE = ROOT / 'fixtures/phase14'
MAINTENANCE_SHA256 = 'f698a6c04a000b8adc29508b74006bab331532979a2dd76c0a4517feb98e487a'
ENGINES = ('QWEN_LOCAL', 'CODEX_AGENT')
MAX_ATTEMPTS = 2
TASK_TTL = 600


class RepairRejected(ValueError):
    """A bounded contract or authorization failure."""


class RepairUnavailable(RuntimeError):
    """Infrastructure unavailable; does not imply a bad repair."""


class _RepeatedCandidate(DraftRejected):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RepairRejected('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(RepairRejected('NONFINITE_JSON')))


def receipt_hash(receipt):
    return digest(encoded({key: value for key, value in receipt.items() if key != 'receipt_sha256'}))


def catalog():
    verify_core()  # Preserve every previously frozen source/security pin.
    return (_catalog(CATALOG, MANIFEST_SHA256) + _catalog(DEVELOPMENT, DEVELOPMENT_SHA256)
            + _catalog(MAINTENANCE, MAINTENANCE_SHA256))


def _catalog(directory, expected):
    path = directory / 'manifest.json'
    if (directory.is_symlink() or path.is_symlink() or not path.is_file()
            or path.stat().st_nlink != 1 or path.stat().st_size>20000
            or digest(path.read_bytes()) != expected):
        raise RepairRejected('OWNED_CATALOG_CHANGED')
    items = strict_json(path.read_bytes())['cases']
    for item in items:
        base = directory / item['id']
        if base.is_symlink() or (base/'tests').is_symlink():
            raise RepairRejected('OWNED_CUSTODY_REJECTED')
        for name, sha in item['sha256'].items():
            file = base/name
            if (file.is_symlink() or not file.is_file() or file.stat().st_nlink != 1
                    or file.stat().st_size > 12000):
                raise RepairRejected('OWNED_CUSTODY_REJECTED')
            if digest(file.read_bytes()) != sha:
                raise RepairRejected('OWNED_BYTES_CHANGED')
    return copy.deepcopy(items)


def source_directory(spec):
    # The directory comes only from pinned manifest membership, never caller data.
    for directory, expected in ((CATALOG,MANIFEST_SHA256),(DEVELOPMENT,DEVELOPMENT_SHA256),
                                (MAINTENANCE,MAINTENANCE_SHA256)):
        if spec in _catalog(directory,expected):return directory/spec['id']
    raise RepairRejected('UNKNOWN_OWNED_SOURCE')


def task_inventory():
    return [{'case_id': item['id'], 'description': item['description'],
             'classification': 'OWNED_DEVELOPMENT', 'independent_evaluation': False}
            for item in catalog()]


def qwen_availability():
    """Admit only the existing pinned bootstrap's assets and loopback process.

    No downloads, process launches, remote requests or credential inspection.
    Health alone never establishes runtime/model identity.
    """
    from bountyforge.phase8_live_qwen import MODEL_SHA256, RUNTIME_SHA256
    base = Path.home()/'.cache/bountyforge'
    model = base/'models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf'
    archive = base/'runtime/llama-b11750-bin-ubuntu-x64.tar.gz'
    try:
        for file, sha in ((model, MODEL_SHA256), (archive, RUNTIME_SHA256)):
            if not file.is_file() or file.is_symlink():
                return False
            with file.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != sha:
                    return False
        # Compare the running executable to the exact pinned archive member.
        with tarfile.open(archive) as bundle:
            members=[m for m in bundle.getmembers()
                     if m.name.removeprefix('./')=='llama-b11750/llama-server' and m.isfile()]
            if len(members)!=1:return False
            member=members[0]
            with bundle.extractfile(member) as stream:
                binary_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        found = False
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                args = (proc/'cmdline').read_bytes().decode().split('\0')
                if (args and Path(args[0]).name == 'llama-server'
                        and args[args.index('-m')+1] == str(model)
                        and args[args.index('--host')+1] == '127.0.0.1'
                        and args[args.index('--port')+1] == '8080'
                        and args[args.index('-np')+1] == '1'):
                    with (proc/'exe').open('rb') as stream:
                        found = hashlib.file_digest(stream, 'sha256').hexdigest() == binary_sha
                    if found:
                        break
            except (OSError, ValueError, IndexError, UnicodeError):
                continue
        if not found:
            return False
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        with opener.open('http://127.0.0.1:8080/health', timeout=1) as reply:
            return strict_json(reply.read(256)).get('status') == 'ok'
    except (OSError, ValueError, KeyError, tarfile.TarError):
        return False


def engine_inventory():
    # A session is not an account-independent unattended inference backend.
    available=qwen_availability()
    return [{'id': 'QWEN_LOCAL', 'label': 'Autonomous Qwen',
             'availability': 'AVAILABLE' if available else 'PINNED_LOCAL_RUNTIME_UNAVAILABLE',
             'unattended_backend_available': available, 'autonomous_mode_supported':True, 'paid_fallback': False},
            {'id': 'CODEX_AGENT', 'label': 'Codex Agent',
             'availability': 'ACTIVE_CODEX_SESSION_REQUIRED',
             'unattended_backend_available': False, 'paid_fallback': False}]


def materialize(spec, root, candidate=None):
    root.mkdir(parents=True)
    (root/'tests').mkdir()
    for name in spec['sha256']:
        (root/name).write_bytes((source_directory(spec)/name).read_bytes())
    (root/FIXTURE_MARKER).write_text('owned-phase12-'+spec['id'])
    if candidate is not None:
        (root/'subject.py').write_text(candidate)
    for file in (root, *root.rglob('*')):
        file.chmod(0o755 if file.is_dir() else 0o644)
    admit(root, 'subject.py', spec['sha256'], candidate=candidate)


class OwnedVerifier:
    def preflight(self):
        return preflight()

    def observe(self, spec, candidate=None):
        # Every observation gets new bytes and a fresh no-network container.
        # Inference credentials are absent from _execute's fixed environment.
        with tempfile.TemporaryDirectory(prefix='bf-dual-verify-') as directory:
            root = Path(directory)/'task'
            materialize(spec, root, candidate)
            result = _execute(root, None, 12)
            admit(root, 'subject.py', spec['sha256'], candidate=candidate)
        if result.get('timeout'):
            raise RepairUnavailable('SANDBOX_TIMEOUT')
        if result.get('error'):
            raise RepairUnavailable('SANDBOX_RESOURCE_OR_CLEANUP_FAILURE')
        try:
            return check_receipt({'passed': result['passed'], 'exit_code': result['returncode'],
                                  'timeout': False, 'output': result['output']})
        except RuntimeError:
            raise RepairUnavailable('SANDBOX_RECEIPT_INVALID') from None


def observation_summary(value):
    value = check_receipt(value)
    total = re.search(r'Ran ([1-9][0-9]*) tests?', value['output'])
    return {'passed': value['passed'], 'exit_code': value['exit_code'],
            'tests_run': int(total.group(1)), 'output_sha256': digest(value['output'].encode()),
            'sandbox': 'digest_pinned_docker_no_network_read_only_no_privileges'}


class RepairService:
    """Process-local capability store. MCP callers cannot inject its verifier."""
    def __init__(self, *, verifier=None, model_factory=None):
        self.verifier = verifier if verifier is not None else OwnedVerifier()
        self.model_factory = model_factory
        self.tasks = {}

    def prepare(self, case_id, engine):
        if engine not in ENGINES or type(case_id) is not str:
            raise RepairRejected('UNKNOWN_ENGINE_OR_OWNED_TASK')
        specs = catalog()
        spec = next((item for item in specs if item['id'] == case_id), None)
        if spec is None or len(self.tasks) >= 4:
            raise RepairRejected('UNKNOWN_OWNED_TASK_OR_SESSION_BUDGET')
        try:
            proof = self.verifier.preflight()
            validate_proof(proof)
        except (RuntimeError, OSError, ValueError):
            raise RepairUnavailable('SANDBOX_ADMISSION_UNAVAILABLE') from None
        try:
            baseline = check_receipt(self.verifier.observe(spec))
        except (RuntimeError, OSError, ValueError):
            raise RepairUnavailable('BASELINE_OBSERVATION_UNAVAILABLE') from None
        if (baseline['passed'] or 'FAIL:' not in baseline['output']
                or 'FAILED (failures=' not in baseline['output'] or 'errors=' in baseline['output']):
            raise RepairRejected('BASELINE_NOT_REPRODUCED_AS_ASSERTION_FAILURE')
        with tempfile.TemporaryDirectory(prefix='bf-dual-prepare-') as directory:
            root=Path(directory)/'task'; materialize(spec,root)
            source=(root/'subject.py').read_text()
            inferred=infer_editable_lines(root,'subject.py',baseline['output'])
            scope=sorted(set(inferred)&set(editable_scope(source,spec['symbol'])))
            units=statement_catalog(source,scope)
        public={'case_id':case_id,'engine':engine,'task_id':uuid.uuid4().hex,'revision':0,
                'source':source,'source_sha256':spec['sha256']['subject.py'],
                'tests_sha256':spec['sha256']['tests/test_regression.py'],
                'target_symbol':spec['symbol'],'description':spec['description'],
                'approved_file':'subject.py','editable_lines':sorted(units),
                'edit_units':[{key:unit[key] for key in ('line','end_line','kind','bindings')}
                              for unit in units.values()],
                'proposal_protocol':'ast_statement_v1','max_attempts':MAX_ATTEMPTS,
                'source_context':source_context(source,spec['symbol'],sorted(units)),
                'baseline_feedback':failure_feedback(baseline['output']),
                'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
                'state':'AWAITING_CODEX_CANDIDATE' if engine=='CODEX_AGENT' else 'QWEN_PREPARED',
                'customer_execution_authorized':False,'delivery_authorized':False}
        self.tasks[public['task_id']]={'public':public,'spec':spec,'scope':scope,
                                     'proof':proof,'created':time.monotonic(),
                                     'attempts':[],'seen':set(),'seen_semantics':set(),'model_calls':0}
        return copy.deepcopy(public)

    def _get(self, task_id, revision, engine=None):
        if type(task_id) is not str or not re.fullmatch(r'[0-9a-f]{32}',task_id):
            raise RepairRejected('UNKNOWN_TASK_CAPABILITY')
        task=self.tasks.get(task_id)
        if task is None or time.monotonic()-task['created'] > TASK_TTL:
            raise RepairRejected('TASK_MISSING_OR_EXPIRED')
        if (type(revision) is not int or revision != task['public']['revision']
                or len(task['attempts']) >= MAX_ATTEMPTS
                or task['public']['state'] in ('AWAITING_OWNER_APPROVAL','BLOCKED','EXHAUSTED')
                or (engine is not None and task['public']['engine'] != engine)):
            raise RepairRejected('REVISION_ENGINE_OR_STATE_REJECTED')
        return task

    def submit(self, task_id, revision, proposal):
        task=self._get(task_id,revision,'CODEX_AGENT')
        return self._submit(task,proposal)

    def _submit(self, task, proposal, *, generation=None):
        public=task['public']; spec=task['spec']
        # Reject JSON ambiguity before existing statement/source validators.
        raw=proposal.encode() if type(proposal) is str else encoded(proposal)
        if len(raw)>3000:
            raise RepairRejected('PROPOSAL_BUDGET_EXCEEDED')
        proposal_sha=digest(raw)
        public_proof={key:task['proof'][key] for key in (*CONTROLS,'image_digest','untrusted_execution_certified')}
        result={'schema':1,'kind':'owned_dual_engine_verification','task_id':public['task_id'],
                'case_id':public['case_id'],'engine':public['engine'],
                'attempt':len(task['attempts'])+1,'revision':public['revision']+1,
                'source_sha256':public['source_sha256'],'tests_sha256':public['tests_sha256'],
                'proposal_sha256':proposal_sha,'proposal':proposal,
                'previous_receipt_sha256':task['attempts'][-1]['receipt_sha256'] if task['attempts'] else None,
                'runtime_admission_sha256':digest(encoded(public_proof)),
                'runtime_admission':public_proof,
                'image':IMAGE,'independently_verified':False,'state':'REVISION_REQUIRED',
                'outcome':'SOURCE_REJECTED','diagnostic':'','failure_stage':'source_validation',
                'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
                'authorship_identity_attested':False,'signature_verified':False,
                'authorship_basis':'local_model_response' if public['engine']=='QWEN_LOCAL' else 'session_submitted_candidate',
                'customer_execution_authorized':False,'delivery_authorized':False,
                'paid_fallback':False}
        if generation is not None:result['generation']=copy.deepcopy(generation)
        if proposal_sha in task['seen']:
            result.update(outcome='REPEATED_PROPOSAL',diagnostic='Identical prior proposal; no test executed')
        else:
            task['seen'].add(proposal_sha)
            try:
                try:
                    strict_json(raw)
                except (ValueError,UnicodeError):
                    raise DraftRejected('Invalid structured JSON proposal') from None
                with tempfile.TemporaryDirectory(prefix='bf-dual-stage-') as directory:
                    root=Path(directory)/'task'; materialize(spec,root)
                    staged=stage_statements(raw.decode(),root,'subject.py',task['scope'],public['source_sha256'])
                    candidate=staged['files'][0]
                    validate_proposal_bindings(public['source'],task['scope'],raw.decode())
                    validate_local_dependencies(public['source'],raw.decode())
                if staged['semantic_sha256'] in task['seen_semantics']:
                    raise _RepeatedCandidate('Equivalent prior AST candidate; no test executed')
                task['seen_semantics'].add(staged['semantic_sha256'])
                result.update(candidate_sha256=digest(candidate['content'].encode()),diff=candidate['diff'])
                result['failure_stage']='targeted_tests'
                first=check_receipt(self.verifier.observe(spec,candidate['content']))
                result['targeted']=observation_summary(first)
                if not first['passed']:result['test_feedback']=failure_feedback(first['output'])
                result.update(outcome='TEST_FAILED',diagnostic='Owned regression failed; follow the public repair contract')
                if first['passed']:
                    result['failure_stage']='independent_replay'
                    final=check_receipt(self.verifier.observe(spec,candidate['content']))
                    result['independent']=observation_summary(final)
                    result.update(outcome='INDEPENDENT_VERIFICATION_FAILED',diagnostic='Fresh replay did not pass')
                    if final['passed']:
                        result.update(outcome='VERIFIED',state='AWAITING_OWNER_APPROVAL',
                                      independently_verified=True,diagnostic='',failure_stage=None,candidate=candidate['content'])
            except _RepeatedCandidate as exc:
                result.update(outcome='REPEATED_PROPOSAL',diagnostic=str(exc))
            except DraftRejected as exc:
                result['diagnostic']=str(exc)[:250]
            except (RuntimeError,OSError) as exc:
                code=str(exc) if isinstance(exc,RepairUnavailable) else 'SANDBOX_OBSERVATION_UNAVAILABLE'
                result.update(outcome='SANDBOX_UNAVAILABLE',state='BLOCKED',diagnostic=code)
        if result['state']=='REVISION_REQUIRED' and result['attempt']==MAX_ATTEMPTS:
            result['state']='EXHAUSTED'
        result['receipt_sha256']=receipt_hash(result)
        task['attempts'].append(copy.deepcopy(result))
        public.update(revision=result['revision'],state=result['state'])
        return result

    def run_qwen(self, task_id, revision):
        task=self._get(task_id,revision,'QWEN_LOCAL')
        if not qwen_availability():
            task['public']['state']='BLOCKED'
            return {'engine':'QWEN_LOCAL','state':'BLOCKED','outcome':'QWEN_UNAVAILABLE',
                    'model_calls':0,'paid_fallback':False,'independently_verified':False}
        model=(self.model_factory or LocalModel)(timeout_seconds=45)
        calls=[]; started=time.monotonic()
        while len(task['attempts'])<MAX_ATTEMPTS:
            previous=task['attempts'][-1] if task['attempts'] else None
            try:prompt=model_prompt(task['public'],previous)
            except ValueError:
                task['public']['state']='BLOCKED'
                return {'engine':'QWEN_LOCAL','state':'BLOCKED','outcome':'CONTEXT_BUDGET_EXHAUSTED',
                        'model_calls':len(calls),'calls':calls,'paid_fallback':False,'independently_verified':False}
            began=time.monotonic()
            call={'response':None,'prompt_sha256':digest(prompt.encode()),'prompt':strict_json(prompt)};calls.append(call)
            try:
                response=model.complete_line(SYSTEM,prompt,max_tokens=150)
                if type(response) is not str or len(response.encode())>3000:
                    raise RuntimeError('Invalid bounded response')
                call.update(response=response,response_sha256=digest(response.encode()),
                            metadata=copy.deepcopy(model.last_call))
            except (RuntimeError,OSError,ValueError,TypeError):
                call['error']='LOCAL_INFERENCE_OR_RESPONSE_UNAVAILABLE'
                task['public']['state']='BLOCKED'
                return {'engine':'QWEN_LOCAL','state':'BLOCKED','outcome':'INFERENCE_UNAVAILABLE',
                        'model_calls':len(calls),'calls':calls,'paid_fallback':False,'independently_verified':False}
            finally:
                if calls:
                    calls[-1]['seconds']=round(time.monotonic()-began,3)
            effective,retained=revision_proposal(previous,response)
            call.update(effective_proposal=effective,retained_anchors=retained)
            result=self._submit(task,effective,generation={
                'raw_response_sha256':digest(response.encode()),'retained_anchors':retained,
                'revision_strategy':strict_json(prompt)['revision_strategy'],
                'prompt_sha256':call['prompt_sha256'],'finish_reason':model.last_call.get('finish_reason') if model.last_call else None})
            if result['state'] in ('AWAITING_OWNER_APPROVAL','BLOCKED','EXHAUSTED'):
                break
        return {**{key:result[key] for key in ('engine','state','outcome','independently_verified')},
                'model_calls':len(calls),'calls':calls,'attempts':copy.deepcopy(task['attempts']),
                'generation_protocol':getattr(model,'protocol','legacy_line_schema'),
                'elapsed_seconds':round(time.monotonic()-started,3),
                'verification_receipt':result,'additional_inference_cost_usd':0,'paid_fallback':False}
