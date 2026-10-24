"""Experimental generation-only contract; final source validators are unchanged.

Not used in the spent Phase21 trials. This fixes two observed wire/validator
mismatches without supplying a patch or expanding source authority.
"""
import json
from phase21_reasoning import output_grammar

PROTOCOL='ast_statement_diagnosis_linked_v1'


def linked_diagnosis_grammar(task):
    lines=output_grammar(task,True).splitlines()
    top=lines[0].removeprefix('root ::= ')
    diagnosis=next(line.removeprefix('diagnosis ::= ') for line in lines if line.startswith('diagnosis ::= '))
    if (top.count(' ws diagnosis ws ')!=1 or top.count(' ws edit (')!=1 or diagnosis.count(' anchor ')!=1):
        raise ValueError('TRUSTED_GRAMMAR_SHAPE_CHANGED')
    branches=[];extra=[]
    for index,unit in enumerate(task['edit_units']):
        name='linked'+str(index);branches.append(name)
        branch=top.replace(' ws diagnosis ws ',' ws diagnosis'+str(index)+' ws ',1)
        branch=branch.replace(' ws edit (',' ws edit'+str(index)+' (',1)
        extra.extend([name+' ::= '+branch,
            'diagnosis'+str(index)+' ::= '+diagnosis.replace(' anchor ',' '+json.dumps(str(unit['line']))+' ',1)])
    lines[0]='root ::= '+' | '.join(branches)
    # Printable raw Unicode plus canonical printable escapes. A Python literal
    # backslash-t is still expressible as JSON double-backslash + t. Actual
    # newlines remain solely in the existing <=2 continuation productions.
    lines=[r'atom ::= [^"\\\x00-\x1f\x7f] | "\\" ["\\/]' if line.startswith('atom ::= ') else line for line in lines]
    return '\n'.join(lines+extra)+'\n'
