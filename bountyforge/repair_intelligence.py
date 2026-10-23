"""Development-only context and revision planning, never new execution authority."""
import ast
import copy
import json
import re
import textwrap


def validate_local_dependencies(source,proposal):
    """Reject newly introduced reads whose first local binding is later.

    Conservative additional guard, not general dataflow verification. Existing
    validators still decide syntax/scope/capabilities. Never executes source.
    """
    from bountyforge.drafts import DraftRejected
    value=json.loads(proposal) if type(proposal) is str else proposal
    tree=ast.parse(source)
    for change in value['changes']:
        line=change['line']
        functions=[f for f in tree.body if isinstance(f,ast.FunctionDef) and f.lineno<line<=f.end_lineno]
        if len(functions)!=1:raise DraftRejected('Ambiguous binding scope')
        function=functions[0]
        old=[n for n in ast.walk(function) if isinstance(n,ast.stmt) and n.lineno==line]
        if len(old)!=1:raise DraftRejected('Ambiguous binding anchor')
        fragment=ast.parse(textwrap.dedent(change['new']),mode='eval' if isinstance(old[0],(ast.If,ast.While)) else 'exec')
        reads=lambda node:{n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
        old_reads=reads(old[0].test if isinstance(old[0],(ast.If,ast.While)) else old[0])
        introduced=reads(fragment)-old_reads
        parameters={a.arg for a in function.args.posonlyargs+function.args.args+function.args.kwonlyargs}
        bindings={}
        for node in ast.walk(function):
            if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Store):
                bindings[node.id]=min(bindings.get(node.id,node.lineno),node.lineno)
        # Comprehension iteration targets are locally defined inside that fragment.
        local_comp={n.id for c in ast.walk(fragment) if isinstance(c,ast.comprehension)
                    for n in ast.walk(c.target) if isinstance(n,ast.Name)}
        for name in introduced-parameters-local_comp:
            if name in bindings and bindings[name]>=line:
                raise DraftRejected('Replacement reads local before its existing binding: '+name)


def failure_feedback(output):
    # Do not include traceback paths or lines from the verifier's test source.
    names=list(dict.fromkeys(re.findall(r'(?:FAIL|ERROR):\s+(test_\w+)',output)))[:8]
    assertions=[row[:180] for row in output.splitlines()
                if re.match(r'^(AssertionError|TypeError|ValueError|KeyError|ZeroDivisionError|NameError|UnboundLocalError|IndexError|AttributeError):',row)][:3]
    return {'failing_tests':names,'assertions':assertions,
            'classification':'OWNED_DEVELOPMENT_FEEDBACK','unseen_evaluation':False}


def source_context(source,symbol,anchors):
    tree=ast.parse(source)
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    target=functions[symbol]
    calls={node.func.id for node in ast.walk(target) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
    terminal=[n for n in target.body if isinstance(n,ast.Return)]
    terminal=terminal[-1:] if terminal else [n for n in ast.walk(target) if isinstance(n,ast.Return)]
    names=lambda n:{x.id for x in ast.walk(n) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Load)}
    distance={name:0 for n in terminal for name in names(n)}
    assignments=[n for n in ast.walk(target) if isinstance(n,(ast.Assign,ast.AnnAssign)) and n.value is not None]
    for depth in range(1,5):
        for node in assignments:
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            bound={x.id for t in targets for x in ast.walk(t) if isinstance(x,ast.Name)}
            if any(distance.get(name,99)<depth for name in bound):
                for name in names(node.value):distance.setdefault(name,depth)
    nodes={n.lineno:n for n in ast.walk(target) if isinstance(n,ast.stmt)}
    def priority(line):
        node=nodes[line]
        if node in assignments:
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            ranks=[distance.get(x.id,99) for t in targets for x in ast.walk(t) if isinstance(x,ast.Name)]
            if ranks and min(ranks)<99:return (0,min(ranks),-line)
        if node in terminal:return (1,0,-line)
        return (2,0,line)
    return {'target_range':[target.lineno,target.end_lineno],
            'called_helpers':sorted((calls & functions.keys())-{symbol}),
            'authorized_anchors':sorted(anchors),
            'prioritized_anchors':sorted(anchors,key=priority),
            'scope_policy':'Only authorized anchors in the target function; helpers are context only'}


def revision_strategy(previous):
    if not previous:return 'INITIAL_MINIMAL_REPAIR'
    if previous['outcome']=='TEST_FAILED':return 'RETAIN_VALID_SIBLINGS_FIX_REMAINING_FAILURES'
    return 'CORRECT_REJECTED_FORMAT_OR_SCOPE'


def revision_proposal(previous,response):
    """Retain only prior source-validated, test-failing edits, then revalidate all.

    A new anchor overrides its old edit. This never salvages rejected source,
    exceeds the three-change bound, or interprets a whole function as an edit.
    """
    if not previous or previous.get('outcome')!='TEST_FAILED' or not previous.get('candidate_sha256'):
        return response,[]
    try:
        from bountyforge.repair_engines import strict_json
        new=strict_json(response)
        old=previous['proposal']
        if type(old) is str:old=strict_json(old)
        def valid(value):
            return (type(value) is dict and set(value)=={'changes'} and type(value['changes']) is list
                    and 1<=len(value['changes'])<=3 and all(type(c) is dict and set(c)=={'line','new'}
                        and type(c['line']) is int and 1<=c['line']<=200 and type(c['new']) is str
                        and len(c['new'].encode())<=400 for c in value['changes'])
                    and len({c['line'] for c in value['changes']})==len(value['changes']))
        if not valid(new) or not valid(old):return response,[]
        replacements={c['line']:c for c in new['changes']}
        retained=[c for c in old['changes'] if c['line'] not in replacements]
        if not retained or len(retained)+len(replacements)>3:return response,[]
        changes=sorted(retained+new['changes'],key=lambda c:c['line'])
        return json.dumps({'changes':changes},separators=(',',':')),[c['line'] for c in retained]
    except (ValueError,KeyError,TypeError):return response,[]


def model_prompt(public,previous):
    data={key:public[key] for key in ('approved_file','source','target_symbol','description',
                                    'editable_lines','edit_units','proposal_protocol')}
    data['source_context']=public['source_context']
    order=public['source_context']['prioritized_anchors']
    data['edit_units']=sorted(data['edit_units'],key=lambda unit:order.index(unit['line']))
    data['failure_feedback']=copy.deepcopy(previous.get('test_feedback',public['baseline_feedback']) if previous else public['baseline_feedback'])
    data['revision_strategy']=revision_strategy(previous)
    if previous:
        data['previous_proposal']=previous['proposal']
        data['previous_error']=previous['diagnostic']
    encode=lambda:json.dumps(data,separators=(',',':'))
    if len(encode().encode())>3600:
        # Drop descriptive duplication, never truncate source or permitted units.
        data.pop('source_context')
        data['failure_feedback']['assertions']=data['failure_feedback']['assertions'][:1]
    if len(encode().encode())>3600:raise ValueError('CONTEXT_BUDGET_EXCEEDED')
    return encode()


def compact_model_prompt(public,previous):
    """Task first; remove duplicate scope metadata, never source or edit units.

    The verifier retains full scope/binding metadata. The wire grammar derives
    names from the exact source. No solution-specific hints or test code.
    """
    feedback=copy.deepcopy(previous.get('test_feedback',public['baseline_feedback']) if previous else public['baseline_feedback'])
    order=public['source_context']['prioritized_anchors']
    units=sorted(public['edit_units'],key=lambda u:order.index(u['line']))
    data={'description':public['description'],'failure_feedback':feedback,
          'revision_strategy':revision_strategy(previous),'target_symbol':public['target_symbol'],
          'source':public['source'],'edit_units':[{k:u[k] for k in ('line','end_line','kind')} for u in units]}
    if previous:data.update(previous_proposal=previous['proposal'],previous_error=previous['diagnostic'])
    raw=json.dumps(data,separators=(',',':'))
    if len(raw.encode())>3600:raise ValueError('CONTEXT_BUDGET_EXCEEDED')
    return raw
