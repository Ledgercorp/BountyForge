"""Documented fixed-origin GETs only. No registration, wallet or submission API."""
import hashlib
import re
import signal
import urllib.error
import urllib.request
from datetime import datetime,timezone
from decimal import Decimal
from bountyforge.repair_engines import strict_json
from bountyforge.crypto_opportunities import normalize_superteam,amount,fresh


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class CryptoReadOnly:
    def __init__(self,token=None):
        if token is not None and (type(token) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{16,180}',token)):
            raise ValueError('PROVIDER_CREDENTIAL_FORMAT_REJECTED')
        self.token=token;self.opener=urllib.request.build_opener(NoRedirect);self.requests=0

    def request(self,provider,operation,*,slug=None,asset=None):
        if provider=='superteam' and operation=='listings':url='https://superteam.fun/api/agents/listings/live?take=20'
        elif provider=='superteam' and operation=='details' and type(slug) is str and re.fullmatch('[a-zA-Z0-9_-]{1,180}',slug):
            url='https://superteam.fun/api/agents/listings/details/'+slug
        elif provider=='coinbase' and operation=='ticker' and asset in ('SOL','USDC','ETH','BTC'):
            url='https://api.exchange.coinbase.com/products/'+asset+'-USD/ticker'
        else:raise ValueError('READ_ONLY_DOCUMENTED_OPERATION_REQUIRED')
        if self.requests>=10:raise ValueError('PUBLIC_REQUEST_BUDGET_EXHAUSTED')
        headers={'User-Agent':'BountyForge-ReadOnly-Crypto-Research','Accept':'application/json'}
        if provider=='superteam' and self.token:headers['Authorization']='Bearer '+self.token
        req=urllib.request.Request(url,headers=headers,method='GET');self.requests+=1
        def expired(*_):raise TimeoutError('PUBLIC_READ_WALL_TIMEOUT')
        old=signal.getsignal(signal.SIGALRM)
        if signal.getitimer(signal.ITIMER_REAL)[0]>0:raise ValueError('NESTED_NETWORK_DEADLINE_REJECTED')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,15)
        observation={'source_url':url,'observed_at':datetime.now(timezone.utc).isoformat(),'method':'GET'}
        try:
            try:
                with self.opener.open(req,timeout=10) as reply:
                    raw=reply.read(256001);status=reply.status
                if len(raw)>256000 or (self.token and self.token.encode() in raw):raise ValueError('UNSAFE_PUBLIC_RESPONSE')
                return {**observation,'status':'OBSERVED','http_status':status,'data':strict_json(raw),'response_sha256':hashlib.sha256(raw).hexdigest()}
            except urllib.error.HTTPError as error:
                return {**observation,'status':'BLOCKED_AUTHENTICATION' if error.code in (401,403) else 'HTTP_ERROR','http_status':error.code}
            except (ValueError,OSError,TimeoutError):return {**observation,'status':'READ_FAILED'}
        finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

    def discover(self):
        observation=self.request('superteam','listings')
        if observation['status']!='OBSERVED':return {**observation,'opportunities':None,'account_created':False,'complete_scan':False}
        rows=observation.pop('data')
        if type(rows) is not list or len(rows)>20:return {**observation,'status':'INVALID_RESPONSE','opportunities':None,'account_created':False,'complete_scan':False}
        items=[];rejected=0
        for row in rows:
            try:items.append(normalize_superteam(row,observation['observed_at']))
            except (ValueError,TypeError):rejected+=1
        return {**observation,'opportunities':items,'malformed_records_rejected':rejected,'account_created':False,'complete_scan':False,'page_limit':20}

    def market_quote(self,asset,*,now=None):
        observation=self.request('coinbase','ticker',asset=asset)
        if observation['status']!='OBSERVED':return {**observation,'asset':asset,'usd_price':None}
        value=observation.pop('data');now=now or observation['observed_at']
        try:
            if type(value) is not dict:raise ValueError('TICKER_OBJECT_REQUIRED')
            price=amount(value.get('price'));bid=amount(value.get('bid'));ask=amount(value.get('ask'));volume=amount(value.get('volume'),zero=True)
            if Decimal(bid)>Decimal(ask) or not fresh(value.get('time'),now,900):raise ValueError('STALE_OR_CROSSED_MARKET')
            return {**observation,'asset':asset,'usd_price':price,'observed_at':now,'market_trade_at':value['time'],'volume_24h':volume,
                    'venue':'Coinbase Exchange public ticker','owner_withdrawal_route_verified':False,'guaranteed_liquidity':False}
        except ValueError:return {**observation,'status':'STALE_OR_INVALID_QUOTE','asset':asset,'usd_price':None}
