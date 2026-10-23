"""Generation-only GBNF for our fixed statement contract, with JSON-safe strings.

The pinned runtime translates string patterns over raw encoded text. Its broad
negated-newline patterns can consume JSON delimiters. Do not compile those
patterns into the wire grammar. Validators remain the authority over patches.
"""
import json
import re


def statement_grammar(schema,*,compact=False):
    changes=schema['properties']['changes']
    alternatives=changes['items']['anyOf']
    if changes.get('minItems')!=1 or changes.get('maxItems')!=3 or not 1<=len(alternatives)<=30:
        raise ValueError('Trusted bounded statement schema required')
    literal=lambda value:json.dumps(value,ensure_ascii=True)
    rules=[
        'root ::= "{" ws '+literal('"changes"')+' ws ":" ws "[" ws edit (ws "," ws edit){0,2} ws "]" ws "}" ws',
        'ws ::= ""' if compact else 'ws ::= [ \\t\\n\\r]{0,8}',
        # Quotation marks and backslashes must be escaped as JSON. Newline is
        # separate to bound physical continuation lines in ordinary output.
        r'atom ::= [^"\\\x00-\x1f] | "\\" (["\\/bfrt] | "u" [0-9a-fA-F]{4})',
        'continuation ::= '+literal('\\n')+' atom{1,100}',
    ]
    names=[];seen=set()
    for index,alternative in enumerate(alternatives):
        props=alternative['properties'];line=props['line']['const']
        if type(line) is not int or not 1<=line<=200 or line in seen:raise ValueError('Trusted unique anchor required')
        seen.add(line);pattern=props['new']['pattern']
        prefix=pattern[1:pattern.index('[^')]
        if not re.fullmatch(r'(?:[A-Za-z_]\w* = |return )?',prefix):raise ValueError('Trusted statement prefix required')
        name='edit'+str(index);names.append(name)
        rules.append(name+' ::= "{" ws '+literal('"line"')+' ws ":" ws '+literal(str(line))+
                     ' ws "," ws '+literal('"new"')+' ws ":" ws '+literal('"'+prefix)+
                     ' atom{1,160} continuation{0,2} '+literal('"')+' ws "}"')
    rules.append('edit ::= '+' | '.join(names))
    return '\n'.join(rules)+'\n'
