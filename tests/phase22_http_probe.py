"""Test-only subprocess: real local HTTP provider simulator, never live HTTPS."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import phase22_deepseek as m
from phase22_budget import Budget

KEY='sk-'+'x'*32
port=int(sys.argv[1]);root=Path(sys.argv[2]);mode=sys.argv[3]
class LocalProvider:
    def open(self,request,timeout):
        if not request.full_url.startswith('https://api.deepseek.com/'):
            raise AssertionError('unexpected destination')
        url='http://127.0.0.1:'+str(port)+request.full_url.removeprefix('https://api.deepseek.com')
        local=urllib.request.Request(url,data=request.data,headers=dict(request.header_items()),method=request.method)
        return urllib.request.build_opener(urllib.request.ProxyHandler({}),m.NoRedirect).open(local,timeout=timeout)

grant={'plan_sha256':'f'*64,'account_sha256':hashlib.sha256(KEY.encode()).hexdigest(),'approved_usd':'2.00','reserve_usd':'20.00',
       'existing_credits_only':True,'no_auto_recharge_confirmed':True,'owner_authorized':True,'expires_unix':2000000000}
client=m.DeepSeekClient(KEY);client._opener=LocalProvider()
if mode=='timeout':m.DEADLINE=0.2
with Budget(root,grant,'f'*64,client.account_sha256) as budget:
    try:
        result=client.generate(budget,'simulated_job',[{'role':'system','content':'JSON only'},{'role':'user','content':'owned neutral input'}],'deepseek-v4-pro')
        status='RETURNED'
    except ValueError:
        result=client.last_evidence;status='REJECTED'
    print(json.dumps({'kind':'SIMULATED_PROVIDER_PROCESS_TEST','status':status,'result':result,'budget':budget.status(),
                      'actual_live_provider_requests':0,'actual_model_generated_repairs':0}))
client.close()
