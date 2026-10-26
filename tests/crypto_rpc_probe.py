"""Test-only real HTTP transport against a local simulator; no live chain calls."""
import json
import sys
import urllib.request
from bountyforge.crypto_receipts import SolanaReadOnly
from bountyforge.crypto_discovery import NoRedirect

port=int(sys.argv[1])
class Local:
    def open(self,request,timeout):
        if request.full_url!='https://api.mainnet-beta.solana.com':raise AssertionError('Unexpected destination')
        mapped=urllib.request.Request('http://127.0.0.1:'+str(port),data=request.data,headers=dict(request.header_items()),method=request.method)
        return urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect).open(mapped,timeout=timeout)

c=SolanaReadOnly();c.opener=Local()
r=c.verify('3'*88,'2'*32,'SOL');b=c.balance('2'*32,'SOL')
print(json.dumps({'kind':'SIMULATED_CHAIN_PROCESS_PROTOCOL_CHECK','simulated':True,'receipt':r,'balance':b,
                  'live_chain_payments_observed':0,'real_earnings_usd':'0'}))
