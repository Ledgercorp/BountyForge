"""GitHub Contents CAS around the existing SQLite queue's bounded state machine.

The remote JSON file is durable; in-memory SQLite is a transaction engine only.
Only trusted synthetic jobs can be enqueued. Discoveries never become runnable.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from bountyforge.autonomy import _issue_url, verify_envelope
from bountyforge.model import _NoRedirect
from bountyforge.queue import Queue

REPO = 'Ledgercorp/BountyForge'
BRANCH = 'state/bountyforge-ledger-v1'
SOURCE_BRANCH = 'engineering/bounded-autonomy-20261020'
STATE_PATH = 'state/ledger.json'
MAX_STATE_BYTES = 512_000
COLUMNS = ('id','state','created','updated','lease_until','attempts','input_json','result_json','lease_token')

class Conflict(RuntimeError):
    pass


def encoded(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>MAX_STATE_BYTES: raise ValueError('Durable state budget exhausted')
    return raw


class GitHubStore:
    """Fixed repository/path/ref; no model-selected network destination or writes."""
    def __init__(self):
        self.token=os.environ.get('GITHUB_TOKEN')
        if not self.token: raise ValueError('Missing repository coordination token')

    def _request(self, path, method='GET', data=None):
        request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/'+path,
            data=None if data is None else json.dumps(data).encode(),method=method,
            headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
                     'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        opener=urllib.request.build_opener(_NoRedirect())
        with opener.open(request,timeout=20) as response:
            raw=response.read(2*MAX_STATE_BYTES+1)
        if len(raw)>2*MAX_STATE_BYTES: raise ValueError('Remote state response budget exceeded')
        return json.loads(raw)

    def read(self):
        try:
            result=self._request('contents/'+STATE_PATH+'?ref='+BRANCH)
        except urllib.error.HTTPError as exc:
            if exc.code==404: return None,None
            raise
        if result.get('type')!='file' or result.get('encoding')!='base64':
            raise ValueError('Unexpected remote state representation')
        raw=base64.b64decode(result['content'])
        if len(raw)>MAX_STATE_BYTES: raise ValueError('Remote state too large')
        return json.loads(raw),result['sha']

    def write(self,state,expected):
        if expected is None:
            # GitHub won't accept PUT on an absent branch. Create only our data ref.
            try:
                self._request('git/ref/heads/'+BRANCH)
            except urllib.error.HTTPError as exc:
                if exc.code!=404: raise
                source=self._request('git/ref/heads/'+SOURCE_BRANCH)
                try:
                    self._request('git/refs','POST',{'ref':'refs/heads/'+BRANCH,'sha':source['object']['sha']})
                except urllib.error.HTTPError as race:
                    if race.code!=422: raise
        payload={'message':'Record bounded BountyForge coordination state','branch':BRANCH,
                 'content':base64.b64encode(encoded(state)).decode()}
        if expected is not None: payload['sha']=expected
        try:
            self._request('contents/'+STATE_PATH,'PUT',payload)
        except urllib.error.HTTPError as exc:
            if exc.code in (409,422): raise Conflict('Concurrent coordination write; no execution admitted') from exc
            raise


class DurableLedger:
    def __init__(self, store): self.store=store

    def _transaction(self, action):
        state,version=self.store.read()
        if state is None: state={'version':1,'jobs':[],'discoveries':[]}
        self._validate(state)
        before=encoded(state)
        queue=Queue(Path(':memory:'))
        try:
            for row in state['jobs']:
                queue.conn.execute('INSERT INTO jobs('+','.join(COLUMNS)+') VALUES('+','.join('?' for _ in COLUMNS)+')',
                                   [row[key] for key in COLUMNS])
            result=action(queue,state)
            state['jobs']=[dict(zip(COLUMNS,row)) for row in queue.conn.execute('SELECT '+','.join(COLUMNS)+' FROM jobs ORDER BY created,id')]
            self._validate(state)
            if encoded(state)!=before or version is None: self.store.write(state,version)
            return result
        finally: queue.close()

    @staticmethod
    def _validate(state):
        encoded(state)
        if not isinstance(state,dict) or set(state)!={'version','jobs','discoveries'} or state['version']!=1:
            raise ValueError('Invalid durable ledger schema')
        if not isinstance(state['jobs'],list) or len(state['jobs'])>100:
            raise ValueError('Repair ledger capacity exhausted')
        if not isinstance(state['discoveries'],list) or len(state['discoveries'])>1000:
            raise ValueError('Discovery ledger capacity exhausted')
        seen=set()
        for job in state['jobs']:
            if not isinstance(job,dict) or set(job)!=set(COLUMNS): raise ValueError('Invalid durable job')
            if not re.fullmatch('[0-9a-f]{64}',job['id']) or job['id'] in seen: raise ValueError('Invalid duplicate durable id')
            seen.add(job['id'])
            data=json.loads(job['input_json'])
            if (not isinstance(data,dict) or set(data)!={'kind','fixture_id','revision','cycle'}
                    or data['kind']!='synthetic' or data['fixture_id']!='addition'
                    or not re.fullmatch('[0-9a-f]{40}',data['revision'])):
                raise ValueError('Unapproved durable execution input')
            if job['state'] not in ('queued','running','failed','review_ready') or type(job['attempts']) is not int or not 0<=job['attempts']<=2:
                raise ValueError('Invalid durable queue state')
            for key in ('created','updated'):
                if type(job[key]) not in (int,float) or not 0<=job[key]<=10**11: raise ValueError('Invalid durable timestamp')
            if job['state']=='running' and (type(job['lease_until']) not in (int,float)
                    or not 0<=job['lease_until']<=10**11 or not isinstance(job['lease_token'],str)
                    or not re.fullmatch('[0-9a-f]{32}',job['lease_token'])):
                raise ValueError('Invalid durable lease')
        seen=set()
        for entry in state['discoveries']:
            if (not isinstance(entry,dict) or set(entry)!={'issue_url','execution_authorized','status'}
                    or not _issue_url(entry['issue_url']) or entry['execution_authorized'] is not False
                    or entry['status']!='unverified_candidate' or entry['issue_url'].lower() in seen):
                raise ValueError('Invalid or overpromoted durable discovery')
            seen.add(entry['issue_url'].lower())

    def discover(self, urls):
        if not isinstance(urls,list) or len(urls)>30: raise ValueError('Discovery budget exceeded')
        def update(queue,state):
            seen={x['issue_url'].lower() for x in state['discoveries']}
            for url in urls:
                if not _issue_url(url): raise ValueError('Untrusted discovery URL')
                if url.lower() not in seen:
                    state['discoveries'].append({'issue_url':url,'status':'unverified_candidate','execution_authorized':False})
                    seen.add(url.lower())
        return self._transaction(update)

    def enqueue_synthetic(self, revision, cycle):
        if not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}',revision): raise ValueError('Exact source revision required')
        if not isinstance(cycle,str) or date.fromisoformat(cycle).isoformat()!=cycle: raise ValueError('UTC cycle date required')
        payload={'kind':'synthetic','fixture_id':'addition','revision':revision,'cycle':cycle}
        job_id=hashlib.sha256(encoded(payload)).hexdigest()
        return self._transaction(lambda queue,state: queue.enqueue(job_id,payload))

    def claim(self):
        return self._transaction(lambda queue,state: queue.claim(lease_seconds=900))

    def finish_failed(self, claim, reason):
        if not isinstance(reason,str) or not re.fullmatch('[a-z_]{1,60}',reason): raise ValueError('Invalid failure code')
        return self._transaction(lambda queue,state: queue.finish(claim['id'],{'status':'failed','error':reason},lease_token=claim['lease_token']))

    def finish_evidence(self,claim,envelope,run_url):
        record=verify_envelope(envelope)
        if (record['bountyforge_revision']!=claim['input']['revision']
                or not re.fullmatch(r'https://github.com/Ledgercorp/BountyForge/actions/runs/[1-9][0-9]*',run_url)):
            raise ValueError('Evidence not bound to this revision and execution')
        ready=record['canary']['status']=='synthetic_review_ready'
        def finish(queue,state):
            now=time.time()
            result={'status':'synthetic_review_ready' if ready else 'failed',
                    'evidence_sha256':envelope['record_sha256'],'run_url':run_url,
                    'commercial_review_ready':False,'external_submission':False}
            res=queue.conn.execute("UPDATE jobs SET state=?,result_json=?,lease_until=NULL,lease_token=NULL,updated=? WHERE id=? AND state='running' AND lease_token=? AND lease_until>=?",
                ('review_ready' if ready else 'failed',json.dumps(result),now,claim['id'],claim['lease_token'],now))
            return res.rowcount==1
        return self._transaction(finish)
