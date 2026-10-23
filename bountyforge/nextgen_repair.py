"""Opt-in owned experiment: fixed larger budget, read-only AST map, no shell."""
import ast
import json
import hashlib
from bountyforge.inference_envelopes import envelope_spec
from bountyforge.profiled_qwen import ProfiledStatementModel,ProfiledInferenceError
from bountyforge.repair_intelligence import compact_model_prompt


def dependency_map(source,symbol):
    if type(source) is not str or len(source.encode())>12000:raise ValueError('BOUNDED_SOURCE_REQUIRED')
    functions={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    if symbol not in functions:raise ValueError('UNKNOWN_TARGET')
    pending=[(symbol,0)];seen=set();result=[]
    while pending and len(result)<6:
        name,depth=pending.pop(0)
        if name in seen:continue
        seen.add(name);node=functions[name]
        calls=sorted({n.func.id for n in ast.walk(node) if isinstance(n,ast.Call)
                      and isinstance(n.func,ast.Name) and n.func.id in functions})[:6]
        result.append({'symbol':name,'range':[node.lineno,node.end_lineno],'calls':calls,'editable':name==symbol})
        if depth<2:pending.extend((name,depth+1) for name in calls if name not in seen)
    return result


def mapped_prompt(public,previous):
    data=json.loads(compact_model_prompt(public,previous))
    data['dependency_map']=dependency_map(public['source'],public['target_symbol'])
    if previous:
        outcome=previous['outcome']
        data['feedback_action']={
            'REPEATED_PROPOSAL':'An unchanged or duplicate candidate cannot improve the test outcome. Choose a different authorized edit.',
            'SOURCE_REJECTED':'Correct the reported format, binding or capability error before changing repair logic.',
            'TEST_FAILED':'Use the exact remaining failures. Previously validated sibling edits are retained and revalidated.',
        }.get(outcome,'Stop if the execution environment is unavailable.')
    raw=json.dumps(data,separators=(',',':'))
    if len(raw.encode())>3600:raise ValueError('CONTEXT_BUDGET_EXCEEDED')
    return raw


class TrialStatementModel(ProfiledStatementModel):
    protocol='nextgen_v1_non_thinking_ast_map'
    maximum_completion_tokens=256
    repair_completion_tokens=256

    def __init__(self,*,timeout_seconds=45,**kwargs):
        # The worker's existing default is not modified. This explicit factory
        # alone chooses the named experiment; no caller-supplied deadline.
        if timeout_seconds!=45:raise ValueError('FIXED_TRIAL_ENVELOPE_REQUIRED')
        super().__init__(timeout_seconds=45,prompt_token_limit=1200,**kwargs)
        self.timeout_seconds=envelope_spec('NEXTGEN_TRIAL')['request_seconds']

    def _post_native(self,path,body):
        if path=='/apply-template':body={**body,'chat_template_kwargs':{'enable_thinking':False}}
        value=super()._post_native(path,body)
        if path=='/apply-template':
            prompt=value.get('prompt') if type(value) is dict else None
            if type(prompt) is not str:raise ProfiledInferenceError('THINKING_TEMPLATE_NOT_VERIFIED')
            # Fail closed if the template ignored non-thinking mode. Do not
            # manually close a reasoning tag or strip/salvage model output.
            tail=prompt.rsplit('<|im_start|>assistant',1)[-1]
            if tail.count('<think>')!=tail.count('</think>'):
                raise ProfiledInferenceError('THINKING_TEMPLATE_NOT_VERIFIED')
            self.template_sha256=hashlib.sha256(prompt.encode()).hexdigest()
        return value

    def complete_line(self,*args,**kwargs):
        self.template_sha256=None
        try:return super().complete_line(*args,**kwargs)
        finally:
            if self.last_call is not None:self.last_call.update(
                template_sha256=self.template_sha256,thinking_disabled=True,resource_envelope='NEXTGEN_TRIAL')
