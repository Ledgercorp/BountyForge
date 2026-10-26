"""Trusted local credit reservations. No provider-enforced cap is implied."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from decimal import Decimal


def microusd(value):
    if type(value) is not str or not re.fullmatch(r'(0|[1-9][0-9]{0,5})(\.[0-9]{1,6})?',value):
        raise ValueError('EXACT_USD_DECIMAL_REQUIRED')
    return int(Decimal(value)*1000000)


def validate_grant(grant,plan,account,*,now=None):
    required={'plan_sha256','account_sha256','approved_usd','reserve_usd','existing_credits_only',
              'no_auto_recharge_confirmed','owner_authorized','expires_unix'}
    if type(grant) is not dict or set(grant)!=required:raise ValueError('EXPLICIT_OWNER_SPEND_GRANT_REQUIRED')
    if any(grant[k] is not True for k in ('owner_authorized','existing_credits_only','no_auto_recharge_confirmed')):
        raise ValueError('EXPLICIT_OWNER_SPEND_GRANT_REQUIRED')
    if (grant['plan_sha256']!=plan or grant['account_sha256']!=account
            or any(type(v) is not str or not re.fullmatch('[a-f0-9]{64}',v) for v in (plan,account))):
        raise ValueError('GRANT_IDENTITY_REJECTED')
    if type(grant['expires_unix']) is not int or grant['expires_unix']<=(time.time() if now is None else now):
        raise ValueError('SPEND_GRANT_EXPIRED')
    cap=microusd(grant['approved_usd']);reserve=microusd(grant['reserve_usd'])
    if not 0<cap<=2000000 or reserve<20000000:raise ValueError('PROPOSED_EXPERIMENT_CEILING_EXCEEDED')
    return cap,reserve


def private(path,directory=False):
    info=path.lstat()
    if (stat.S_ISLNK(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077
            or (not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1))
            or (directory and not stat.S_ISDIR(info.st_mode))):raise ValueError('PRIVATE_STATE_REQUIRED')


class Budget:
    def __init__(self,root,grant,plan,account):
        self.root=Path(root);self.grant=grant;self.plan=plan;self.account=account
        self.cap,self.reserve_floor=validate_grant(grant,plan,account)
        self.lock=None;self.db=None

    def __enter__(self):
        try:
            private(self.root,True)
            fd=os.open(self.root/'active.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            self.lock=os.fdopen(fd,'r+b');private(self.root/'active.lock')
            try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('ONE_ACTIVE_EXPERIMENT_REQUIRED') from None
            file=self.root/'budget.sqlite'
            try:
                fd=os.open(file,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
            except FileExistsError:pass
            private(file)
            self.db=sqlite3.connect(file,timeout=2,isolation_level=None)
            self.db.execute('PRAGMA synchronous=FULL');self.db.execute('PRAGMA journal_mode=DELETE')
            if self.db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('BUDGET_STATE_CORRUPT')
            self.db.executescript('CREATE TABLE IF NOT EXISTS identity (id INTEGER PRIMARY KEY CHECK(id=1), plan TEXT, account TEXT, grant_sha TEXT); CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, case_id TEXT NOT NULL, attempt INTEGER NOT NULL, reserved INTEGER NOT NULL CHECK(reserved>0), charged INTEGER, usage TEXT, UNIQUE(case_id,attempt));')
            grant_sha=hashlib.sha256(json.dumps(self.grant,sort_keys=True).encode()).hexdigest()
            identity=(self.plan,self.account,grant_sha)
            row=self.db.execute('SELECT plan,account,grant_sha FROM identity WHERE id=1').fetchone()
            if row is None:self.db.execute('INSERT INTO identity VALUES(1,?,?,?)',identity)
            elif row!=identity:raise ValueError('BUDGET_IDENTITY_CHANGED')
            return self
        except (OSError,sqlite3.Error,ValueError) as error:
            self.__exit__(None,None,None)
            if isinstance(error,ValueError):raise
            raise ValueError('PRIVATE_BUDGET_STATE_UNAVAILABLE') from None

    def __exit__(self,*_):
        if self.db is not None:self.db.close();self.db=None
        if self.lock is not None:self.lock.close();self.lock=None

    def reserve(self,case,balance_usd,cost):
        validate_grant(self.grant,self.plan,self.account)
        if (self.root/'STOP').exists():raise ValueError('EXPERIMENT_STOPPED')
        if (type(case) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,63}',case)
                or type(cost) is not int or cost<=0):raise ValueError('RESERVATION_REJECTED')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            used,pending=self.db.execute('SELECT COALESCE(SUM(COALESCE(charged,reserved)),0), COALESCE(SUM(CASE WHEN charged IS NULL THEN reserved ELSE 0 END),0) FROM requests').fetchone()
            if self.db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]>=12:
                raise ValueError('EXPERIMENT_REQUEST_LIMIT')
            attempt=self.db.execute('SELECT COUNT(*) FROM requests WHERE case_id=?',(case,)).fetchone()[0]+1
            if attempt>2:raise ValueError('TASK_ATTEMPT_LIMIT')
            if used+cost>self.cap:raise ValueError('CUMULATIVE_BUDGET_DENIED')
            if microusd(balance_usd)-pending-cost<self.reserve_floor:raise ValueError('CREDIT_RESERVE_DENIED')
            row=self.db.execute('INSERT INTO requests(case_id,attempt,reserved) VALUES(?,?,?)',(case,attempt,cost))
            self.db.execute('COMMIT')
            return {'id':row.lastrowid,'attempt':attempt,'reserved_microusd':cost}
        except Exception:
            self.db.execute('ROLLBACK');raise

    def settle(self,request_id,cost,usage):
        if type(cost) is not int or cost<0 or type(usage) is not dict:raise ValueError('USAGE_REJECTED')
        row=self.db.execute('SELECT reserved,charged FROM requests WHERE id=?',(request_id,)).fetchone()
        if row is None or row[1] is not None or cost>row[0]:raise ValueError('UNCERTAIN_OR_EXCESS_USAGE_RETAINS_RESERVATION')
        raw=json.dumps(usage,sort_keys=True,allow_nan=False)
        self.db.execute('UPDATE requests SET charged=?,usage=? WHERE id=? AND charged IS NULL',(cost,raw,request_id))

    def status(self):
        used,unknown,total=self.db.execute('SELECT COALESCE(SUM(COALESCE(charged,reserved)),0),SUM(charged IS NULL),COUNT(*) FROM requests').fetchone()
        return {'committed_microusd':used,'unknown_requests':unknown or 0,'reserved_requests':total,
                'approved_microusd':self.cap,'reserve_microusd':self.reserve_floor,'provider_enforced_cap':False}
