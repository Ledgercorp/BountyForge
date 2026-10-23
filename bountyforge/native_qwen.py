"""Pinned llama.cpp native schema transport, still numeric loopback only.

The model's own apply-template route renders chat; no hand-authored template or
remote fallback. Independent validators remain authoritative after generation.
"""
import json
import urllib.parse
import urllib.request
from bountyforge.model import _NoRedirect
from bountyforge.qwen_statement_contract import AdaptiveStatementModel


class NativeStatementModel(AdaptiveStatementModel):
    protocol='qwen_native_statement_schema_v4'

    def _post_native(self,path,body):
        parsed=urllib.parse.urlsplit(self.endpoint)  # Constructor validates approved host/port.
        url=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,path,'',''))
        request=urllib.request.Request(url,data=json.dumps(body).encode(),method='POST',
                                       headers={'Content-Type':'application/json'})
        try:
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
            with opener.open(request,timeout=self.timeout_seconds) as response:
                raw=response.read(65537)
                if len(raw)>65536:raise ValueError('Native response bound exceeded')
                return json.loads(raw)
        except (OSError,ValueError,RuntimeError):
            raise RuntimeError('Pinned native loopback inference unavailable; no fallback') from None

    def _complete_bounded_schema(self,system,user,max_tokens,schema,name):
        self.last_call=None
        if (type(system) is not str or type(user) is not str or len(system.encode())>3600
                or len(user.encode())>3600 or type(max_tokens) is not int or not 1<=max_tokens<=150):
            raise ValueError('Bounded native request required')
        template=self._post_native('/apply-template',{'messages':[
            {'role':'system','content':system},{'role':'user','content':user}],
            'add_generation_prompt':True})
        if type(template) is not dict:raise RuntimeError('Invalid model template response')
        prompt=template.get('prompt')
        if type(prompt) is not str or len(prompt.encode())>16000:raise RuntimeError('Invalid model template response')
        value=self._post_native('/completion',{'prompt':prompt,'n_predict':max_tokens,
              'temperature':0,'stream':False,'json_schema':schema,'cache_prompt':False})
        if type(value) is not dict:raise RuntimeError('Invalid native model response')
        text=value.get('content')
        self.last_call={'prompt_tokens':value.get('tokens_evaluated'),
                        'completion_tokens':value.get('tokens_predicted'),
                        'finish_reason':'length' if value.get('stop_type')=='limit' else value.get('stop_type'),
                        'transport':'llama_native_completion_schema'}
        if type(text) is not str or not text.strip() or len(text.encode())>3000:
            raise RuntimeError('Invalid bounded native model response')
        return text.strip()
