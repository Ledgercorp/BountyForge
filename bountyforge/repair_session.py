"""Opt-in owned repair sessions around the frozen statement worker.

No executor, provider or source permission is selected here. The trusted caller
must supply pinned owned bytes and an independently admitted test runner. All
patches still pass the existing statement/capability validator. No customer
source intake, publication, payment or delivery capability is implemented.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import json
import re
import shutil
import tempfile
import textwrap
import time
from pathlib import Path

from bountyforge.curated_tasks import editable_scope
from bountyforge.drafts import DraftRejected, safe_path
from bountyforge.line_scope import infer_editable_lines
from bountyforge.repair_context import build_prompt, diagnostic_summary
from bountyforge.statements import SYSTEM, stage_statements, statement_catalog
from bountyforge.worker import FIXTURE_MARKER, repair_fixture

PROTOCOL = 'owned_statement_session_v8'
SESSION_SYSTEM = SYSTEM + (
    ' Prefer the smallest expression-level correction within an existing statement. '
    'Do not expand a compact statement into a loop or introduce new attribute capabilities. '
    'Use complete supplied test methods, their fixtures, and actual latest failure evidence. '
    'A previous proposal metric exceeding a limit is a rejection, not executable feedback. '
    'Do not claim tests passed or choose commands; independent verification decides success.'
)
HEX = re.compile(r'[0-9a-f]{64}\Z')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_receipt(value):
    """Reject contradictory, incomplete and timed-out observations, never run code."""
    if (not isinstance(value, dict) or type(value.get('passed')) is not bool
            or type(value.get('exit_code')) is not int or value['exit_code'] not in (0, 1)
            or value.get('timeout') is not False or not isinstance(value.get('output'), str)
            or len(value['output'].encode()) > 6000
            or re.search(r'Ran [1-9][0-9]* tests?', value['output']) is None):
        raise RuntimeError('Incomplete isolated regression receipt')
    passed = value['exit_code'] == 0 and value['output'].rstrip().endswith('OK')
    failed = value['exit_code'] == 1 and 'FAILED (' in value['output']
    if value['passed'] != passed or (not passed and not failed):
        raise RuntimeError('Contradictory isolated regression receipt')
    return copy.deepcopy(value)


def admit(root, path, hashes, *, candidate=None):
    root=Path(root)
    if root.is_symlink() or not root.is_dir() or path != 'subject.py':
        raise DraftRejected('Only pinned flat owned fixtures are supported')
    if (not isinstance(hashes, dict) or set(hashes) != {path, 'tests/test_regression.py'}
            or any(not isinstance(v,str) or not HEX.fullmatch(v) for v in hashes.values())):
        raise DraftRejected('Exact owned source/test pins required')
    files=set(); directories=set()
    for entry in root.rglob('*'):
        if entry.is_symlink() or not (entry.is_file() or entry.is_dir()):
            raise DraftRejected('Unsupported owned fixture object')
        name=entry.relative_to(root).as_posix()
        if entry.is_dir(): directories.add(name)
        else:
            info=entry.stat()
            if info.st_nlink != 1 or info.st_size > 12000:
                raise DraftRejected('Owned fixture file exceeds bounds')
            files.add(name)
    if directories != {'tests'} or files != {path,'tests/test_regression.py',FIXTURE_MARKER}:
        raise DraftRejected('Unexpected owned fixture content')
    marker=(root/FIXTURE_MARKER).read_text()
    if not marker.startswith('owned-') or len(marker.encode()) > 100:
        raise DraftRejected('Owned fixture identity required')
    for name, expected in hashes.items():
        raw=(root/name).read_bytes()
        wanted=digest(candidate.encode()) if name == path and candidate is not None else expected
        if digest(raw) != wanted:
            raise DraftRejected('Pinned owned fixture bytes changed')
    return root


def contract_units(contract, failure):
    """Whole methods and transitive test fixtures/helpers, without evaluation."""
    tree=ast.parse(contract)
    methods=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)
             and (n.name.startswith('test') or n.name in ('setUp','setUpClass'))]
    if len({n.name for n in methods}) != len(methods):
        raise DraftRejected('Ambiguous controlled test method names')
    failing=set(re.findall(r'(test_\w+)',failure))
    methods.sort(key=lambda n:(0 if n.name in ('setUp','setUpClass') else 1 if n.name in failing else 2,n.lineno))
    candidates=[]
    def add(node, owner=None):
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            names={n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)}
        elif isinstance(node,ast.FunctionDef) and node not in methods:
            names={node.name}
        elif isinstance(node,(ast.Import,ast.ImportFrom)):
            names={a.asname or a.name.split('.')[0] for a in node.names}
        else:return
        code=ast.unparse(node)
        if owner:code='class '+owner+':\n'+'\n'.join('    '+row for row in code.split('\n'))
        candidates.append((node,names,code))
    for node in tree.body:
        if isinstance(node,ast.ClassDef):
            for child in node.body:add(child,node.name)
        else:add(node)
    selected=[]; pending=list(methods); names=set()
    while pending:
        for node in pending:
            names.update(n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load))
            names.update(n.attr for n in ast.walk(node) if isinstance(n,ast.Attribute))
        pending=[]
        for node,defined,code in candidates:
            if defined & names and all(node is not chosen[0] for chosen in selected):
                selected.append((node,code)); pending.append(node)
    selected.sort(key=lambda entry:entry[0].lineno)
    return [('fixture',code) for _,code in selected]+[(n.name,ast.unparse(n)) for n in methods]


def validate_proposal_bindings(source, scope, response):
    """Stricter conservative guards, not general Python data-flow verification."""
    try:
        changes=json.loads(response)['changes']; catalog=statement_catalog(source,scope)
        tree=ast.parse(source)
        for change in changes:
            unit=catalog[change['line']]; text=change['new']
            if unit['kind']=='condition':
                expressions=[n.test for n in ast.walk(tree) if isinstance(n,(ast.If,ast.While))
                             and n.lineno==change['line']]
                old={n.target.id for expr in expressions for n in ast.walk(expr)
                     if isinstance(n,ast.NamedExpr) and isinstance(n.target,ast.Name)}
                new={n.target.id for n in ast.walk(ast.parse(text.strip(),mode='eval'))
                     if isinstance(n,ast.NamedExpr) and isinstance(n.target,ast.Name)}
                if not old<=new:raise DraftRejected('Replacement lost existing condition binding')
            else:
                fragment=ast.parse(textwrap.dedent(text))
                functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)
                           and n.lineno < change['line'] <= n.end_lineno]
                bound=set()
                if len(functions)==1:
                    function=functions[0]
                    bound.update(a.arg for a in function.args.posonlyargs+function.args.args+function.args.kwonlyargs)
                    for node in function.body:
                        if node.lineno>=change['line']:break
                        if isinstance(node,(ast.Assign,ast.AnnAssign)) and getattr(node,'value',None) is not None:
                            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                            bound.update(n.id for target in targets for n in ast.walk(target)
                                         if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store))
                for node in fragment.body:
                    if isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id not in bound:
                        raise DraftRejected('Replacement reads uninitialized augmented assignment binding')
                    if isinstance(node,(ast.Assign,ast.AnnAssign)) and getattr(node,'value',None) is not None:
                        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                        bound.update(n.id for target in targets for n in ast.walk(target)
                                     if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store))
    except (ValueError,TypeError,KeyError,SyntaxError,AttributeError) as exc:
        if isinstance(exc,DraftRejected):raise
        raise DraftRejected('Invalid bounded binding proposal') from None


def proposal_metrics(raw):
    try:
        value=json.loads(raw); changes=value['changes']
        if not isinstance(changes,list):raise ValueError()
        return {'physical_lines':[len(c['new'].split('\n')) for c in changes],
                'replacement_bytes':[len(c['new'].encode()) for c in changes],
                'changes':len(changes)}
    except (ValueError,TypeError,KeyError,AttributeError):
        return {'parseable_change_metrics':False}


def make_prompt(source,path,scope,issue,contract,baseline,latest,previous,error):
    # Reuse the frozen source/dependency extractor, retaining exact physical lines.
    _, prepared=build_prompt(source,path,scope,dict(issue,repair_protocol='ast_contract_v5',
                            test_contract_untrusted='',previous_proposal='',prior_error='',test_failure_excerpt=''))
    source_data=json.loads(prepared)
    units=statement_catalog(source,scope)
    contracts=contract_units(contract,latest)
    included=[]; omitted=[]
    for name, code in contracts:
        if len(('\n'.join(c for _,c in included)+code).encode()) <= 1400:
            included.append((name,code))
        else: omitted.append(name)
    data={'edit_protocol':PROTOCOL,'approved_file':path,'target_symbol':issue['target_symbol'],
          'editable_lines':sorted(units),'source_lines_untrusted':source_data['source_lines_untrusted'],
          'edit_units':[[u['line'],u['end_line'],u['kind'],u['bindings']] for u in units.values()],
          'edit_unit_columns':['anchor','end','kind','required_bindings'],
          'issue_untrusted':str(issue.get('description_excerpt',''))[:400],
          'test_contract_untrusted':'\n'.join(c for _,c in included),
          'omitted_contract_units':omitted,'test_contract_complete':not omitted,
          'failure_untrusted':diagnostic_summary(latest,600),
          'previous_error':str(error)[:250],'previous_proposal':previous if len(previous.encode())<=600 else '',
          'previous_response_sha256':digest(previous.encode()) if previous else None,
          'previous_proposal_metrics':proposal_metrics(previous) if previous else None,
          'validator_constraints':{'max_changes':3,'max_physical_lines':3,'max_replacement_bytes':400,
                                   'existing_attributes':sorted({n.attr for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Attribute)}),
                                   'new_attributes_prohibited':True}}
    if diagnostic_summary(baseline) != diagnostic_summary(latest):
        data['baseline_failure_untrusted']=diagnostic_summary(baseline,250)
    encode=lambda:json.dumps(data,ensure_ascii=True)
    # Drop only whole nonfailing tests, preserving failing test identity and fixtures.
    failing=set(re.findall(r'test_\w+',latest))
    while len(encode().encode()) > 3600:
        removable=[i for i,(name,_) in enumerate(included) if name.startswith('test') and name not in failing]
        if not removable:break
        name,_=included.pop(removable[-1]); omitted.append(name)
        data.update(test_contract_untrusted='\n'.join(c for _,c in included),
                    omitted_contract_units=omitted,test_contract_complete=False)
    if len(encode().encode()) > 3600:
        data['previous_proposal']=''; data['issue_untrusted']=data['issue_untrusted'][:150]
    if len(encode().encode()) > 3600 or not any(name in failing for name,_ in included):
        raise DraftRejected('Complete failing contract does not fit bounded context')
    return encode()


def repair_owned(issue, fixture_root, approved_path, model, *, expected_hashes, test_runner, max_attempts=2):
    """Reuse existing bounded worker; one source, deterministic scope, no host fallback."""
    path=safe_path(approved_path)
    if type(max_attempts) is not int or not 1 <= max_attempts <= 2 or not callable(test_runner):
        raise DraftRejected('Explicit owned test runner and bounded attempt count required')
    if not isinstance(issue,dict) or issue.get('verification')!='unverified_candidate':
        raise DraftRejected('Owned unverified issue required')
    root=admit(fixture_root,path,expected_hashes)
    source=(root/path).read_text(); contract=(root/'tests/test_regression.py').read_text()
    result={'schema':1,'protocol':PROTOCOL,'status':'blocked','patch':None,'model_calls':0,
            'calls':[],'baseline_cache_reads':0,'customer_execution_authorized':False,
            'delivery_authorized':False,'paid_fallback':False,'source_sha256':expected_hashes[path],
            'tests_sha256':expected_hashes['tests/test_regression.py']}
    started=time.monotonic(); baseline=None; latest=None; previous=''
    def observe(work):
        try:
            value=test_runner(work)
        except Exception:
            raise RuntimeError('Isolated regression unavailable') from None
        return check_receipt(value)
    try:
        with tempfile.TemporaryDirectory(prefix='bf-owned-session-baseline-') as directory:
            original=Path(directory)/'baseline'; shutil.copytree(root,original)
            baseline=observe(original); admit(original,path,expected_hashes)
        if (baseline['passed'] or 'FAIL:' not in baseline['output']
                or 'FAILED (failures=' not in baseline['output'] or 'errors=' in baseline['output']):
            result['reason']='baseline_not_assertion_failure'; return result
        result['baseline']=baseline; latest=baseline['output']
        try:
            inferred=infer_editable_lines(root,path,baseline['output'])
            scope=sorted(set(inferred)&set(editable_scope(source,issue.get('target_symbol'))))
            target=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)
                    and n.name==issue.get('target_symbol')]
            if len(target)!=1 or not scope or any(not target[0].lineno < n <= target[0].end_lineno for n in inferred):
                raise DraftRejected('Scope mismatch')
        except (DraftRejected,SyntaxError,ValueError):
            result['reason']='scope_rejected';return result
        result['editable_lines']=scope
        class SessionModel:
            last_call=None
            def complete_line(self,system,prepared,max_tokens):
                nonlocal previous
                if system != SYSTEM:raise DraftRejected('Unexpected statement preparation')
                data=json.loads(prepared)
                try:
                    prompt=make_prompt(source,path,scope,issue,contract,baseline['output'],latest,
                                       previous,data.get('previous_error',''))
                except (DraftRejected,ValueError,TypeError):
                    result['context_preparation_failed']=True
                    raise RuntimeError('Bounded context unavailable') from None
                call={'number':len(result['calls'])+1,'system':SESSION_SYSTEM,'prompt':prompt,
                      'max_tokens':max_tokens,'prepared_prompt_sha256':digest(prepared.encode()),
                      'previous_response_sha256':digest(previous.encode()) if previous else None,
                      'response':None}
                result['calls'].append(call); result['model_calls']+=1
                began=time.monotonic()
                try:
                    self.last_call=None
                    try:
                        model.last_call=None
                        response=model.complete_line(SESSION_SYSTEM,prompt,max_tokens)
                        if not isinstance(response,str):raise RuntimeError('Invalid response')
                    except Exception:
                        raise RuntimeError('Owned inference unavailable') from None
                    call.update(response=response,response_sha256=digest(response.encode()))
                    previous=response
                    validate_proposal_bindings(source,scope,response)
                    return response
                except DraftRejected as exc:
                    call['source_rejection']=str(exc)[:250];raise
                except Exception as exc:
                    call['error']=type(exc).__name__;raise
                finally:
                    call['seconds']=round(time.monotonic()-began,3)
                    self.last_call=copy.deepcopy(getattr(model,'last_call',None));call['metadata']=self.last_call
        def guarded_runner(work):
            nonlocal latest
            current=(Path(work)/path).read_text()
            if current == source:
                admit(work,path,expected_hashes);result['baseline_cache_reads']+=1
                return copy.deepcopy(baseline)
            try:
                candidate=stage_statements(previous,root,path,scope,expected_hashes[path])['files'][0]['content']
                if current!=candidate:raise DraftRejected('Candidate lacks exact response binding')
                admit(work,path,expected_hashes,candidate=candidate)
                observation=observe(work)
                admit(work,path,expected_hashes,candidate=candidate)
            except DraftRejected as exc:
                raise RuntimeError('Owned regression custody changed') from exc
            latest=observation['output'];return observation
        # Blank only the frozen worker's redundant prepared contract. Actual
        # provider context is constructed above from the exact pinned full tests.
        prepared_issue=dict(issue,test_contract_untrusted='')
        worker=repair_fixture(prepared_issue,root,[path],SessionModel(),max_attempts=max_attempts,
                              strategy='statement',editable_lines={path:scope},test_runner=guarded_runner)
        result['worker']=worker
        # Nested worker calls describe its prepared context, not transmitted
        # provider requests. Preserve this distinction instead of relabeling them.
        result['worker_call_context']='prepared_before_session_middleware; actual calls are top-level calls'
        blocked=(not result['calls'] or result['model_calls'] != worker['model_calls'] or
                 worker.get('error')=='independent_verification_failed' or
                 any(a.get('error')=='model_or_runner_unavailable' for a in worker['attempts']))
        result['status']='blocked' if blocked else worker['status']
        if worker['status']=='review_ready' and not blocked:
            check_receipt(worker['independent_verification'])
            candidate=stage_statements(previous,root,path,scope,expected_hashes[path])['files'][0]
            if worker['patch'] != [{'path':path,'diff':candidate['diff']}]:raise RuntimeError('Patch binding failed')
            result['patch']=worker['patch'];result['candidate_sha256']=digest(candidate['content'].encode())
        result['reason']=('context_rejected_before_inference' if not result['calls'] or result.get('context_preparation_failed')
                          else 'inference_or_regression_unavailable') if blocked else None
    except (RuntimeError,OSError,DraftRejected,ValueError):
        result.update(status='blocked',patch=None,reason='owned_session_admission_or_runner_failed')
    finally:
        result['elapsed_seconds']=round(time.monotonic()-started,3)
    return result
