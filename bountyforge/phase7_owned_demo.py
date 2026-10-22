"""Offline, owned-only fulfillment rehearsal. Never accepts customer code or money."""
import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path

SOURCE = b'def total(a, b):\n    return a - b\n'
PATCHED = b'def total(a, b):\n    return a + b\n'
SOURCE_HASH = hashlib.sha256(SOURCE).hexdigest()
PATCHED_HASH = hashlib.sha256(PATCHED).hexdigest()
STATES = ('CREATED','SCOPE_REVIEWED','PROPOSED','VERIFIED','AWAITING_OWNER_APPROVAL','HELD')


class SyntheticBlocked(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def replay(source, patched):
    """Only exact, hard-coded owned bytes can reach compile/exec."""
    if type(source) is not bytes or type(patched) is not bytes or source != SOURCE or patched != PATCHED:
        raise SyntheticBlocked('Unapproved fixture bytes')
    baseline, repaired = {'__builtins__':{}}, {'__builtins__':{}}
    exec(compile(source,'<owned-source>','exec'),baseline)
    exec(compile(patched,'<owned-repair>','exec'),repaired)
    cases=((1,2,3),(-10,8,-2),(7,9,16),(0,0,0))
    if (not any(baseline['total'](a,b)!=want for a,b,want in cases)
            or not all(repaired['total'](a,b)==want for a,b,want in cases)):
        raise SyntheticBlocked('Owned replay failed')
    return {'kind':'owned_replay','baseline_failed':True,'repair_passed':True,
            'vectors':len(cases),'source_sha256':SOURCE_HASH,'patch_sha256':PATCHED_HASH,
            'customer_code_executed':False,'model_calls':0}


def require_private_directory(directory):
    directory=Path(directory)
    try:
        st=directory.lstat()
        if (not directory.is_absolute() or not stat.S_ISDIR(st.st_mode)
                or st.st_uid!=os.getuid() or st.st_mode & 0o077):
            raise SyntheticBlocked('Private directory required')
    except OSError:
        raise SyntheticBlocked('Private directory unavailable') from None
    return directory


def package_record(job):
    return {'schema':1,'kind':'owned_review_package','job_id':job,
            'source_sha256':SOURCE_HASH,'patch_sha256':PATCHED_HASH,
            'owned_replay_passed':True,'real_payment_verified':False,
            'customer_rights_verified':False,'model_sharing_authorized':False,
            'private_execution_authorized':False,'delivery_authorized':False,
            'model_calls':0,'received_revenue_usd':0}


class OwnedOnlyLedger:
    """SQLite CAS coordination for a single fixed owned fixture, not paid intake."""
    def __init__(self, path):
        path=Path(path)
        require_private_directory(path.parent)
        if not path.is_absolute() or path.is_symlink():
            raise SyntheticBlocked('Invalid synthetic ledger location')
        if path.exists():
            st=path.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_mode & 0o077:
                raise SyntheticBlocked('Synthetic ledger file not private')
        else:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            os.close(fd)
        self.db=sqlite3.connect(str(path),isolation_level=None,timeout=5)
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, step TEXT NOT NULL, rev INTEGER NOT NULL, evidence TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT, rev INTEGER, step TEXT, evidence_sha TEXT, PRIMARY KEY(id,rev))')

    def close(self):
        self.db.close()

    def read(self, job):
        if job != 'synthetic_0123456789abcdef':
            raise SyntheticBlocked('Only fixed owned synthetic ID permitted')
        row=self.db.execute('SELECT step,rev,evidence FROM jobs WHERE id=?',(job,)).fetchone()
        return None if row is None else {'step':row[0],'rev':row[1],'evidence':json.loads(row[2])}

    def create(self, job):
        if job != 'synthetic_0123456789abcdef':
            raise SyntheticBlocked('Only fixed synthetic ID permitted')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.db.execute('SELECT id FROM jobs WHERE id=?',(job,)).fetchone()
            created=row is None
            if created:
                evidence={'kind':'owned_fixture','source_sha256':SOURCE_HASH,'real_payment_verified':False}
                self.db.execute('INSERT INTO jobs VALUES (?,?,?,?)',(job,'CREATED',0,canonical(evidence).decode()))
                self.db.execute('INSERT INTO events VALUES (?,?,?,?)',(job,0,'CREATED',digest(canonical(evidence))))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return created

    def advance(self, job, expected_rev, step, evidence, *, package_path=None):
        if type(expected_rev) is not int or expected_rev<0 or type(evidence) is not dict:
            raise SyntheticBlocked('Invalid revision or evidence')
        rules={
            'SCOPE_REVIEWED':('CREATED',{'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False}),
            'PROPOSED':('SCOPE_REVIEWED',{'kind':'owned_patch','patch_sha256':PATCHED_HASH}),
            'VERIFIED':('PROPOSED',replay(SOURCE,PATCHED)),
            'AWAITING_OWNER_APPROVAL':('VERIFIED',{'kind':'owned_package','package_sha256':digest(canonical(package_record(job))+b'\n'),'delivery_authorized':False}),
            'HELD':(None,{'kind':'owned_hold','delivery_authorized':False}),
        }
        if step not in rules or evidence != rules[step][1]:
            raise SyntheticBlocked('Unauthorized synthetic transition evidence')
        if step=='AWAITING_OWNER_APPROVAL':
            expected_name=job+'.review.json'
            p=Path(package_path) if package_path is not None else Path('/nonexistent')
            if p.name!=expected_name or p.is_symlink():
                raise SyntheticBlocked('Synthetic review package missing')
            require_private_directory(p.parent)
            try:
                fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
                try:
                    info=os.fstat(fd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_mode & 0o077:
                        raise SyntheticBlocked('Review package file not private')
                    raw=os.read(fd,8192)
                finally:
                    os.close(fd)
            except OSError:
                raise SyntheticBlocked('Review package unavailable') from None
            if raw!=canonical(package_record(job))+b'\n':
                raise SyntheticBlocked('Review package changed')
        elif package_path is not None:
            raise SyntheticBlocked('Unexpected package in review step')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.read(job)
            if row is None or row['rev']!=expected_rev or row['step']=='HELD':
                raise SyntheticBlocked('Expired or revoked synthetic revision')
            if step!='HELD' and row['step']!=rules[step][0]:
                raise SyntheticBlocked('Synthetic transition sequence rejected')
            nextrev=expected_rev+1
            self.db.execute('UPDATE jobs SET step=?,rev=?,evidence=? WHERE id=?',
                            (step,nextrev,canonical(evidence).decode(),job))
            self.db.execute('INSERT INTO events VALUES (?,?,?,?)',
                            (job,nextrev,step,digest(canonical(evidence))))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return nextrev


def owned_demo(ledger, directory):
    job='synthetic_0123456789abcdef'
    require_private_directory(directory)
    if not ledger.create(job) or ledger.read(job)['step']!='CREATED':
        raise SyntheticBlocked('Owned demo already used')
    rev=ledger.advance(job,0,'SCOPE_REVIEWED',{'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False})
    rev=ledger.advance(job,rev,'PROPOSED',{'kind':'owned_patch','patch_sha256':PATCHED_HASH})
    rev=ledger.advance(job,rev,'VERIFIED',replay(SOURCE,PATCHED))
    file=Path(directory)/(job+'.review.json')
    raw=canonical(package_record(job))+b'\n'
    try:
        fd=os.open(file,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        try:
            while raw:
                n=os.write(fd,raw)
                if n<=0:
                    raise SyntheticBlocked('Package write failed')
                raw=raw[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        raise SyntheticBlocked('Private review package cannot be written') from None
    rev=ledger.advance(job,rev,'AWAITING_OWNER_APPROVAL',
                       {'kind':'owned_package',
                        'package_sha256':digest(canonical(package_record(job))+b'\n'),
                        'delivery_authorized':False},package_path=file)
    return {'kind':'owned_only_fulfillment_demo','job_id':job,'state':ledger.read(job)['step'],
            'revision':rev,'package_sha256':digest(file.read_bytes()),
            'owned_replay_passed':True,'real_payment_verified':False,
            'private_execution_authorized':False,'delivery_authorized':False,
            'model_calls':0,'received_revenue_usd':0}
