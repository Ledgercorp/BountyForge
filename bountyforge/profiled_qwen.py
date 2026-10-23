"""Same pinned native generation, with a measured context admission boundary."""
from bountyforge.native_qwen import NativeStatementModel


class ProfiledInferenceError(RuntimeError):
    pass


class ProfiledStatementModel(NativeStatementModel):
    protocol='qwen_json_safe_grammar_v6_context_checked'

    def _post_native(self,path,body):
        if path=='/completion':
            self.failure_stage='tokenization'
            tokens=super()._post_native('/tokenize',{'content':body['prompt'],'add_special':False,'parse_special':True})
            values=tokens.get('tokens') if type(tokens) is dict else None
            if type(values) is not list or not values or not all(type(x) is int and x>=0 for x in values):
                raise ProfiledInferenceError('TOKENIZER_RESPONSE_INVALID')
            self.tokenized_prompt_tokens=len(values)
            if len(values)+body['n_predict']>2048:raise ProfiledInferenceError('CONTEXT_LIMIT_EXCEEDED')
            self.dispatched_completions=1
        self.failure_stage=path.strip('/').replace('-','_')
        return super()._post_native(path,body)

    def _complete_bounded_schema(self,*args,**kwargs):
        self.dispatched_completions=0;self.tokenized_prompt_tokens=None;self.failure_stage='request_validation'
        try:return super()._complete_bounded_schema(*args,**kwargs)
        except ProfiledInferenceError:raise
        except RuntimeError:raise ProfiledInferenceError('LOCAL_'+self.failure_stage.upper()+'_UNAVAILABLE') from None
        finally:
            self.last_call={**(self.last_call or {}),'completion_requests':self.dispatched_completions,
                            'tokenized_prompt_tokens':self.tokenized_prompt_tokens}
