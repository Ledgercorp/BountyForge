"""Development-only context and revision planning, never new execution authority."""
import ast
import copy
import json
import re


def failure_feedback(output):
    # Do not include traceback paths or lines from the verifier's test source.
    names=list(dict.fromkeys(re.findall(r'(?:FAIL|ERROR):\s+(test_\w+)',output)))[:8]
    assertions=[row[:180] for row in output.splitlines()
                if re.match(r'^(AssertionError|TypeError|ValueError|KeyError|ZeroDivisionError|NameError):',row)][:3]
    return {'failing_tests':names,'assertions':assertions,
            'classification':'OWNED_DEVELOPMENT_FEEDBACK','unseen_evaluation':False}


def source_context(source,symbol,anchors):
    tree=ast.parse(source)
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    target=functions[symbol]
    calls={node.func.id for node in ast.walk(target) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}
    return {'target_range':[target.lineno,target.end_lineno],
            'called_helpers':sorted((calls & functions.keys())-{symbol}),
            'authorized_anchors':sorted(anchors),
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
