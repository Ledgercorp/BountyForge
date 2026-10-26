"""Documented fixed-origin GETs only. No registration, wallet or submission API."""
import hashlib
import re
import signal
import urllib.error
import urllib.request
from urllib.parse import urlencode
from datetime import datetime,timezone
from decimal import Decimal
from bountyforge.repair_engines import strict_json
from bountyforge.crypto_opportunities import normalize_superteam,normalize_github,amount,fresh


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
        elif provider=='github' and operation in ('search_open_python_bounties','search_algora_python_bounties'):
            # Fixed public-search queries: no caller-controlled URL or query.
            # Three records keep issue bodies within our small response cap.
            query=('bounty language:python is:open is:issue' if operation=='search_open_python_bounties'
                   else 'commenter:app/algora-pbc language:python is:open is:issue')
            params=urlencode({'q':query,'per_page':3,'sort':'updated','order':'desc'})
            url='https://api.github.com/search/issues?'+params
        elif provider=='coinbase' and operation=='ticker' and asset in ('SOL','USDC','ETH','BTC'):
            url='https://api.exchange.coinbase.com/products/'+asset+'-USD/ticker'
        else:raise ValueError('READ_ONLY_DOCUMENTED_OPERATION_REQUIRED')
        if self.requests>=10:raise ValueError('PUBLIC_REQUEST_BUDGET_EXHAUSTED')
        headers={'User-Agent':'BountyForge-ReadOnly-Crypto-Research','Accept':'application/json'}
        if provider=='superteam' and self.token:headers['Authorization']='Bearer '+self.token
        if provider=='github':headers['X-GitHub-Api-Version']='2022-11-28'
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
                if len(raw)>256000:return {**observation,'status':'RESPONSE_TOO_LARGE','http_status':status}
                if self.token and self.token.encode() in raw:raise ValueError('UNSAFE_PUBLIC_RESPONSE')
                rate_headers={}
                if provider=='github':
                    response_headers=getattr(reply,'headers',{})
                    rate_headers={'rate_limit_remaining':response_headers.get('X-RateLimit-Remaining'),
                                  'rate_limit_resource':response_headers.get('X-RateLimit-Resource'),
                                  'rate_limit_reset':response_headers.get('X-RateLimit-Reset')}
                return {**observation,**rate_headers,'status':'OBSERVED','http_status':status,'data':strict_json(raw),'response_sha256':hashlib.sha256(raw).hexdigest()}
            except urllib.error.HTTPError as error:
                status=('BLOCKED_AUTHENTICATION' if error.code in (401,403) else 'HTTP_ERROR')
                if provider=='github' and error.code in (403,429):status='RATE_LIMIT_OR_ACCESS_RESTRICTED'
                return {**observation,'status':status,'http_status':error.code}
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

    def discover_github(self,*,algora_bot=False):
        """Read one fixed public GitHub query; every match remains unverified."""
        operation='search_algora_python_bounties' if algora_bot else 'search_open_python_bounties'
        observation=self.request('github',operation)
        if observation['status']!='OBSERVED':
            return {**observation,'opportunities':None,'complete_scan':False,'page_limit':3,
                    'source_role':'PUBLIC_SEARCH_LEADS_ONLY','authenticated':False}
        payload=observation.pop('data')
        if (type(payload) is not dict or type(payload.get('total_count')) is not int
                or type(payload.get('incomplete_results')) is not bool
                or type(payload.get('items')) is not list or len(payload['items'])>3):
            return {**observation,'status':'INVALID_RESPONSE','opportunities':None,'complete_scan':False,
                    'page_limit':3,'source_role':'PUBLIC_SEARCH_LEADS_ONLY','authenticated':False}
        items=[];rejected=0;excluded_pull_requests=0
        for row in payload['items']:
            if type(row) is not dict:
                rejected+=1;continue
            if 'pull_request' in row:
                excluded_pull_requests+=1;continue
            try:
                labels=row.get('labels',[])
                if type(labels) is not list:labels=[]
                bounded={k:row.get(k) for k in ('html_url','title','body','state','created_at','updated_at')}
                bounded['labels']=[x.get('name','')[:80] for x in labels[:20] if type(x) is dict]
                items.append(normalize_github(bounded,observation['observed_at']))
            except (ValueError,TypeError):rejected+=1
        return {**observation,'opportunities':items,'total_matches':payload['total_count'],
                'incomplete_results':payload['incomplete_results'],'malformed_records_rejected':rejected,
                'pull_requests_excluded':excluded_pull_requests,'complete_scan':False,'page_limit':3,
                'source_role':'PUBLIC_SEARCH_LEADS_ONLY','authenticated':False,
                'query_class':'ALGORA_BOT_COMMENTER' if algora_bot else 'BROAD_BOUNTY_TERM'}

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
