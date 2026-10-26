"""Credential-bearing trusted HTTPS broker; no listener, tools, installs or fallback.

The controller supplies only frozen owned inputs. Model output remains inert
until a separate credential-free Docker verifier admits it. Billing reservations
are application bounds, NOT a provider-enforced account spending guarantee.
"""
import hashlib
import json
import re
import signal
import time
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_CEILING
from bountyforge.repair_engines import strict_json
from phase22_budget import Budget, microusd

BASE='https://api.deepseek.com'
MODELS={'deepseek-flash':('0.30','1.20'),'deepseek-v4-pro':('1.32','3.96')}
MAX_INPUT=16384
MAX_OUTPUT=4096
MAX_RESPONSE=131072
DEADLINE=120


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def usd_balance(value):
    if type(value) is not dict or value.get('is_available') is not True:raise ValueError('ACCOUNT_UNAVAILABLE')
    rows=value.get('balance_infos')
    if type(rows) is not list or len(rows)!=1 or rows[0].get('currency')!='USD':raise ValueError('EXACT_USD_BALANCE_REQUIRED')
    row=rows[0]
    total=microusd(row.get('total_balance'));granted=microusd(row.get('granted_balance'));topped=microusd(row.get('topped_up_balance'))
    if total!=granted+topped:raise ValueError('BALANCE_INCONSISTENT')
    return row['total_balance']


def admitted_models(value):
    if type(value) is not dict or value.get('object')!='list' or type(value.get('data')) is not list:
        raise ValueError('MODEL_INVENTORY_REJECTED')
    selected={}
    for row in value['data']:
        if type(row) is not dict or row.get('id') not in MODELS:continue
        if (row.get('owned_by')!='deepseek' or type(row.get('context_window')) is not int
                or row['context_window']<MAX_INPUT+MAX_OUTPUT or type(row.get('max_output_tokens')) is not int
                or row['max_output_tokens']<MAX_OUTPUT or 'text' not in row.get('output_modalities',[])):
            raise ValueError('MODEL_CAPABILITY_UNCONFIRMED')
        selected[row['id']]=row
    return selected


def cost_upper(model,prompt,completion):
    inp,out=map(Decimal,MODELS[model])
    # Prices USD / million tokens yield microUSD / token. Peak, cache-miss,
    # all completion including reasoning; no discount or free-tier assumption.
    return int((Decimal(prompt)*inp+Decimal(completion)*out).to_integral_value(rounding=ROUND_CEILING))


def parse_usage(value,model):
    if model not in MODELS or type(value) is not dict:raise ValueError('USAGE_UNCONFIRMED')
    usage={}
    for name,limit in (('prompt_tokens',MAX_INPUT),('completion_tokens',MAX_OUTPUT),('total_tokens',MAX_INPUT+MAX_OUTPUT)):
        v=value.get(name)
        if type(v) is not int or not 0<=v<=limit:raise ValueError('USAGE_UNCONFIRMED')
        usage[name]=v
    if usage['total_tokens']!=usage['prompt_tokens']+usage['completion_tokens']:raise ValueError('USAGE_INCONSISTENT')
    for name in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens'):
        if name in value:
            v=value[name]
            if type(v) is not int or not 0<=v<=usage['prompt_tokens']:raise ValueError('CACHE_USAGE_REJECTED')
            usage[name]=v
    if all(n in usage for n in ('prompt_cache_hit_tokens','prompt_cache_miss_tokens')) and usage['prompt_cache_hit_tokens']+usage['prompt_cache_miss_tokens']!=usage['prompt_tokens']:
        raise ValueError('CACHE_USAGE_REJECTED')
    detail=value.get('completion_tokens_details',{})
    reasoning=detail.get('reasoning_tokens') if type(detail) is dict else None
    if reasoning is not None and (type(reasoning) is not int or not 0<=reasoning<=usage['completion_tokens']):
        raise ValueError('REASONING_USAGE_REJECTED')
    usage['reasoning_tokens']=reasoning
    return usage,cost_upper(model,usage['prompt_tokens'],usage['completion_tokens'])


def parse_response(value,model):
    if type(value) is not dict or value.get('model')!=model:raise ValueError('PROVIDER_MODEL_MISMATCH')
    usage,cost=parse_usage(value.get('usage'),model)
    choices=value.get('choices')
    if type(choices) is not list or len(choices)!=1:raise ValueError('CHOICE_COUNT_REJECTED')
    choice=choices[0]
    if type(choice) is not dict:raise ValueError('PROVIDER_CHOICE_REJECTED')
    message=choice.get('message',{})
    if choice.get('finish_reason')!='stop' or type(message) is not dict or message.get('role')!='assistant':
        raise ValueError('INCOMPLETE_PROVIDER_RESPONSE')
    if any(message.get(k) for k in ('tool_calls','function_call')):raise ValueError('MODEL_TOOL_CALL_REJECTED')
    content=message.get('content')
    if type(content) is not str or not 1<=len(content.encode())<=3000:raise ValueError('CANDIDATE_BYTE_LIMIT')
    obj=strict_json(content)
    if type(obj) is not dict or set(obj)!={'changes'}:raise ValueError('PATCH_SCHEMA_REQUIRED')
    return {'content':content,'usage':usage,'cost_upper_microusd':cost,'provider_confirmed_cost':False,
            'model':model,'provider_response_id':str(value.get('id',''))[:120]}


class DeepSeekClient:
    def __init__(self,key):
        if type(key) is not str or not re.fullmatch(r'sk-[A-Za-z0-9_-]{20,128}',key):raise ValueError('CREDENTIAL_FORMAT_REJECTED')
        self.__key=key
        self.account_sha256=hashlib.sha256(key.encode()).hexdigest()
        self._opener=urllib.request.build_opener(NoRedirect)
        self.__pending=False
        self.last_evidence=None
        self.completion_requests_dispatched=0

    def close(self):self.__key=None

    def call(self,method,path,payload=None):
        if (method,path) not in {('GET','/models'),('GET','/user/balance'),('POST','/chat/completions')}:
            raise ValueError('ENDPOINT_OR_METHOD_NOT_ALLOWED')
        if method=='GET' and payload is not None:raise ValueError('METADATA_BODY_NOT_ALLOWED')
        if method=='POST' and not self.__pending:raise ValueError('AUTHORIZED_BUDGET_REQUIRED')
        if self.__key is None:raise ValueError('CREDENTIAL_CLOSED')
        body=None if payload is None else json.dumps(payload,separators=(',',':'),allow_nan=False).encode()
        if body is not None and len(body)>MAX_INPUT+4096:raise ValueError('REQUEST_BYTE_LIMIT')
        request=urllib.request.Request(BASE+path,data=body,method=method,
            headers={'Authorization':'Bearer '+self.__key,'Content-Type':'application/json',
                     'Accept':'application/json','User-Agent':'BountyForge/Phase22'})
        def expired(*_):raise TimeoutError('PROVIDER_WALL_DEADLINE')
        # urllib's socket timeout alone does not bound periodic whitespace.
        prior=signal.getsignal(signal.SIGALRM);old_timer=signal.getitimer(signal.ITIMER_REAL)
        if old_timer[0]>0:raise ValueError('NESTED_PROVIDER_TIMER_REJECTED')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,DEADLINE)
        try:
            try:
                if method=='POST':
                    self.completion_requests_dispatched+=1
                    self.last_evidence['http_completion_dispatched']=True
                with self._opener.open(request,timeout=DEADLINE) as response:
                    if response.status!=200:raise ValueError('PROVIDER_STATUS_REJECTED')
                    raw=response.read(MAX_RESPONSE+1)
                if len(raw)>MAX_RESPONSE:raise ValueError('PROVIDER_RESPONSE_LIMIT')
                if self.__key.encode() in raw:raise ValueError('PROVIDER_SECRET_ECHO_REJECTED')
                return strict_json(raw)
            except ValueError:raise
            except Exception:raise ValueError('PROVIDER_REQUEST_UNCERTAIN') from None
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)

    def inspect(self):
        balance=self.call('GET','/user/balance');usd_balance(balance)
        models=self.call('GET','/models');admitted_models(models)
        return {'balance':balance,'models':models,'auto_recharge':'NOT_EXPOSED_BY_API',
                'credit_expiration':'NOT_EXPOSED_BY_API','inference_requests':0}

    def generate(self,budget,case,messages,model):
        if type(budget) is not Budget:raise ValueError('AUTHORIZED_BUDGET_REQUIRED')
        if budget.account!=self.account_sha256:raise ValueError('ACCOUNT_GRANT_MISMATCH')
        if model not in MODELS:raise ValueError('MODEL_NOT_ALLOWED')
        if (type(messages) is not list or len(messages)!=2
                or any(type(m) is not dict or set(m)!={'role','content'} or type(m['content']) is not str for m in messages)
                or [m['role'] for m in messages]!=['system','user']):raise ValueError('BOUNDED_OWNED_MESSAGES_REQUIRED')
        if any(self.__key in m['content'] for m in messages):raise ValueError('CREDENTIAL_IN_PROMPT_REJECTED')
        # Conservative byte-based estimate with framing margin; exact provider
        # tokenization is unavailable locally. Reserve the whole input envelope.
        if len(json.dumps(messages,ensure_ascii=False).encode())+1024>MAX_INPUT:raise ValueError('INPUT_ENVELOPE_EXCEEDED')
        balance=usd_balance(self.call('GET','/user/balance'))
        reservation=budget.reserve(case,balance,cost_upper(model,MAX_INPUT,MAX_OUTPUT))
        began=time.monotonic()
        self.last_evidence={'reservation':reservation,'status':'UNKNOWN_REQUEST','model':model,
                            'provider':'https://api.deepseek.com','usage':None,'provider_confirmed_cost':False,'http_completion_dispatched':False}
        payload={'model':model,'messages':messages,'max_tokens':MAX_OUTPUT,'stream':False,
                 'response_format':{'type':'json_object'},'thinking':{'type':'enabled'},'reasoning_effort':'high'}
        self.__pending=True
        try:
            value=self.call('POST','/chat/completions',payload)
            # Account returned usage even if the patch or finish reason is rejected.
            if type(value) is not dict or value.get('model')!=model:raise ValueError('PROVIDER_MODEL_MISMATCH')
            usage,cost=parse_usage(value.get('usage'),model)
            budget.settle(reservation['id'],cost,usage)
            self.last_evidence.update(usage=usage,cost_upper_microusd=cost,status='RETURNED_USAGE_ACCOUNTED')
            choices=value.get('choices');message=choices[0].get('message') if type(choices) is list and len(choices)==1 and type(choices[0]) is dict else None
            content=message.get('content') if type(message) is dict else None
            if type(content) is str and len(content.encode())<=12000:self.last_evidence['returned_candidate']=content
            result=parse_response(value,model)
            self.last_evidence.update(status='RETURNED_CANDIDATE',provider_response_id=result['provider_response_id'])
            return result
        except Exception as error:
            self.last_evidence['diagnostic']=str(error) if re.fullmatch('[A-Z_]{1,80}',str(error)) else 'PROVIDER_RESPONSE_REJECTED'
            raise ValueError(self.last_evidence['diagnostic']) from None
        finally:
            self.__pending=False;self.last_evidence['seconds']=round(time.monotonic()-began,3)
