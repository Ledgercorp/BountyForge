"""Generation constraints only. Existing AST, capability and test gates still apply."""
import ast
import json
import re
from bountyforge.model import LocalModel


def statement_schema(source, units):
    tree=ast.parse(source)
    nodes={node.lineno:node for node in ast.walk(tree) if isinstance(node,ast.stmt)}
    alternatives=[]
    for unit in units:
        line=unit['line'];node=nodes.get(line)
        pattern=r'^[^\r\n]{1,400}$'
        if unit['kind']=='statement':
            if isinstance(node,ast.Return):pattern=r'^return [^\r\n]{1,390}$'
            elif (isinstance(node,ast.Assign) and len(node.targets)==1
                  and isinstance(node.targets[0],ast.Name)):
                pattern='^'+re.escape(node.targets[0].id)+r' = [^\r\n]{1,350}$'
        alternatives.append({'type':'object','properties':{
            'line':{'type':'integer','const':line},
            'new':{'type':'string','maxLength':400,'pattern':pattern}},
            'required':['line','new'],'additionalProperties':False})
    if not 1<=len(alternatives)<=30:raise ValueError('Trusted AST units required')
    return {'type':'object','properties':{'changes':{'type':'array','minItems':1,'maxItems':3,
            'items':{'anyOf':alternatives}}},'required':['changes'],'additionalProperties':False}


class StatementModel(LocalModel):
    protocol='qwen_statement_schema_v2'

    def complete_line(self,system,user,max_tokens=150):
        self.last_call=None
        if (type(system) is not str or type(user) is not str or len(user.encode())>3600
                or type(max_tokens) is not int or not 1<=max_tokens<=150):
            raise ValueError('Bounded statement request required')
        task=json.loads(user)
        schema=statement_schema(task['source'],task['edit_units'])
        instruction=('Output only the JSON patch. Each new value is ONE replacement statement, '
                     'or ONLY the expression for a condition unit. Never output the whole function. '
                     'Use the exact assigned name and spaces around = for assignments. '
                     'Do not include Markdown or explanation. ')
        return self._complete_bounded_schema(instruction+system,user,max_tokens,schema,self.protocol)


class AdaptiveStatementModel(StatementModel):
    """Still AST anchored; allow bounded continuation lines rather than functions."""
    protocol='qwen_statement_schema_v3'

    def complete_line(self,system,user,max_tokens=150):
        self.last_call=None
        if (type(system) is not str or type(user) is not str or len(user.encode())>3600
                or type(max_tokens) is not int or not 1<=max_tokens<=150):
            raise ValueError('Bounded statement request required')
        task=json.loads(user);schema=statement_schema(task['source'],task['edit_units'])
        for alternative in schema['properties']['changes']['items']['anyOf']:
            spec=alternative['properties']['new'];pattern=spec['pattern']
            # Preserve the trusted first-statement prefix and cap at three physical lines.
            spec['pattern']=pattern[:-1]+r'(\n[^\r\n]{1,180}){0,2}$'
        instruction=('JSON only. Patch the authorized statements, never the function definition. '
                     'You may change up to three related anchors. Assignment names must remain bound. '
                     'Condition units accept expressions only. Use exact failure feedback. '
                     'On retry, prior validated edits at other anchors are retained and all edits revalidated. ')
        return self._complete_bounded_schema(instruction+system,user,max_tokens,schema,self.protocol)
