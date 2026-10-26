"""Solana read RPC and conservative native SOL / canonical USDC receipt parser.

No signing, private keys, token approvals, transfers, faucets or trading methods.
A chain receipt alone does NOT establish owner control or spendable USD income.
"""
import json
import re
import signal
import urllib.error
import urllib.request
from datetime import datetime,timezone
from bountyforge.crypto_discovery import NoRedirect
from bountyforge.crypto_opportunities import USDC_SOLANA
from bountyforge.repair_engines import strict_json,receipt_hash

RPC='https://api.mainnet-beta.solana.com'
BASE58=re.compile(r'[1-9A-HJ-NP-Za-km-z]+\Z')


def identity(value,kind):
    if type(value) is not str or not BASE58.fullmatch(value) or not ((32<=len(value)<=44) if kind=='wallet' else (64<=len(value)<=90)):
        raise ValueError('PUBLIC_CHAIN_IDENTITY_REJECTED')
    return value


def parse_finalized(tx,status,signature,wallet,asset):
    identity(signature,'signature');identity(wallet,'wallet')
    if tx is None:raise ValueError('TRANSACTION_UNCONFIRMED_OR_PRUNED')
    try:
        slot=tx['slot'];s=status['value'][0];meta=tx['meta'];transaction=tx['transaction']
        if (type(slot) is not int or type(s) is not dict or s['slot']!=slot or s['err'] is not None
                or s['confirmationStatus']!='finalized' or meta['err'] is not None
                or transaction['signatures'][0]!=signature):raise ValueError('FINALITY_OR_TRANSACTION_REJECTED')
        keys=[x['pubkey'] if type(x) is dict else x for x in transaction['message']['accountKeys']]
        if len(keys)!=len(set(keys)):raise ValueError('AMBIGUOUS_ACCOUNT_KEYS')
        if asset=='SOL':
            i=keys.index(wallet)
            pre=meta['preBalances'];post=meta['postBalances']
            if len(pre)!=len(keys) or len(post)!=len(keys) or any(type(n) is not int or n<0 for n in pre+post):raise ValueError('BALANCE_SHAPE_REJECTED')
            delta=post[i]-pre[i];decimals=9
        elif asset=='USDC':
            def total(rows):
                result=0;seen=set()
                for row in rows:
                    if row.get('owner')!=wallet or row.get('mint')!=USDC_SOLANA:continue
                    i=row['accountIndex'];units=row['uiTokenAmount'];value=units['amount']
                    if (type(i) is not int or not 0<=i<len(keys) or i in seen or units['decimals']!=6
                            or type(value) is not str or not re.fullmatch('[0-9]{1,20}',value) or int(value)>=2**64):
                        raise ValueError('TOKEN_BALANCE_REJECTED')
                    seen.add(i);result+=int(value)
                return result
            delta=total(meta['postTokenBalances'])-total(meta['preTokenBalances']);decimals=6
        else:raise ValueError('PAYMENT_ASSET_UNSUPPORTED')
        if delta<=0:raise ValueError('NO_POSITIVE_NET_RECEIPT')
    except (KeyError,IndexError,TypeError,AttributeError):raise ValueError('RPC_RECEIPT_INCOMPLETE') from None
    return {'kind':'SOLANA_FINALIZED_NET_RECEIPT','network':'solana-mainnet','signature':signature,'wallet':wallet,'asset':asset,
            'mint':USDC_SOLANA if asset=='USDC' else None,'amount_base_units':delta,'decimals':decimals,'slot':slot,
            'owner_control_attested':False,'spendable_usd':None,'legal_payout_route_verified':False,'provider_signature_verified':False}


class SolanaReadOnly:
    def __init__(self):self.opener=urllib.request.build_opener(NoRedirect);self.requests=0

    def rpc(self,method,params):
        if method not in ('getTransaction','getSignatureStatuses','getBalance','getTokenAccountsByOwner','getHealth'):
            raise ValueError('READ_ONLY_RPC_METHOD_REQUIRED')
        if self.requests>=8:raise ValueError('RPC_READ_BUDGET_EXHAUSTED')
        self.requests+=1;request_id=self.requests
        raw=json.dumps({'jsonrpc':'2.0','id':request_id,'method':method,'params':params},separators=(',',':')).encode()
        if len(raw)>2000:raise ValueError('RPC_INPUT_BOUND')
        request=urllib.request.Request(RPC,data=raw,method='POST',headers={'Content-Type':'application/json','User-Agent':'BountyForge-ReadOnly-Payment-Observer'})
        def expired(*_):raise TimeoutError('RPC_READ_TIMEOUT')
        old=signal.getsignal(signal.SIGALRM)
        if signal.getitimer(signal.ITIMER_REAL)[0]>0:raise ValueError('NESTED_RPC_TIMEOUT')
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,15)
        try:
            try:
                with self.opener.open(request,timeout=10) as r:body=r.read(256001)
                if len(body)>256000:raise ValueError('RPC_RESPONSE_BOUND')
                value=strict_json(body)
                if type(value) is not dict or value.get('id')!=request_id or 'error' in value or 'result' not in value:
                    raise ValueError('RPC_RESULT_UNCONFIRMED')
                return value['result']
            except (OSError,TimeoutError):raise ValueError('RPC_READ_UNAVAILABLE') from None
        finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

    def verify(self,signature,wallet,asset):
        identity(signature,'signature');identity(wallet,'wallet')
        if asset not in ('SOL','USDC'):raise ValueError('PAYMENT_ASSET_UNSUPPORTED')
        tx=self.rpc('getTransaction',[signature,{'encoding':'jsonParsed','commitment':'finalized','maxSupportedTransactionVersion':0}])
        status=self.rpc('getSignatureStatuses',[[signature],{'searchTransactionHistory':True}])
        record=parse_finalized(tx,status,signature,wallet,asset)
        record.update(source=RPC,checked_at=datetime.now(timezone.utc).isoformat(),verification_scope='SINGLE_TRUSTED_PUBLIC_RPC_OBSERVATION')
        record['receipt_sha256']=receipt_hash(record)
        return record

    def balance(self,wallet,asset):
        identity(wallet,'wallet')
        if asset=='SOL':
            r=self.rpc('getBalance',[wallet,{'commitment':'finalized'}]);value=r['value']
            if type(value) is not int or value<0:raise ValueError('BALANCE_REJECTED')
            return {'asset':asset,'balance_base_units':value,'slot':r['context']['slot'],'decimals':9}
        if asset!='USDC':raise ValueError('PAYMENT_ASSET_UNSUPPORTED')
        r=self.rpc('getTokenAccountsByOwner',[wallet,{'mint':USDC_SOLANA},{'encoding':'jsonParsed','commitment':'finalized'}]);total=0
        for row in r['value']:
            info=row['account']['data']['parsed']['info'];units=info['tokenAmount']
            if info['owner']!=wallet or info['mint']!=USDC_SOLANA or units['decimals']!=6:raise ValueError('TOKEN_OWNER_OR_MINT_REJECTED')
            if type(units['amount']) is not str or not re.fullmatch('[0-9]{1,20}',units['amount']):raise ValueError('TOKEN_UNITS_REJECTED')
            total+=int(units['amount'])
        return {'asset':asset,'balance_base_units':total,'slot':r['context']['slot'],'decimals':6}
