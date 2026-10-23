"""Durable, bounded owned-task coordination; not a customer execution queue.

Only fixed catalog identities enter this store. A live session is still required
to author Codex proposals. Database progress never substitutes for fresh tests.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid

from bountyforge.repair_engines import (RepairService, RepairRejected, RepairUnavailable, ENGINES,
    catalog, digest, encoded, strict_json, receipt_hash)
from bountyforge.phase8_evaluation import validate_proof
from bountyforge.curated_docker import IMAGE

DEFAULT_PATH = Path(__file__).resolve().parents[1]/'.bountyforge-owned-queue/state.sqlite3'
LEASE_SECONDS = 180
JOB_SECONDS = 600
MAX_CLAIMS = 2
MAX_ATTEMPTS = 2


def valid_success(receipt,case_id,engine,task_id=None):
    """Checksums detect corruption, not malicious edits by the same trusted UID."""
    try:
        spec=next(item for item in catalog() if item['id']==case_id)
        validate_proof(receipt['runtime_admission'])
        observations=[receipt['targeted'],receipt['independent']]
        proposal=receipt['proposal']
        raw=proposal.encode() if type(proposal) is str else encoded(proposal)
        return (receipt.get('kind')=='owned_dual_engine_verification'
                and receipt.get('receipt_sha256')==receipt_hash(receipt)
                and receipt.get('runtime_admission_sha256')==digest(encoded(receipt['runtime_admission']))
                and receipt.get('case_id')==case_id and receipt.get('engine')==engine
                and (task_id is None or receipt.get('task_id')==task_id)
                and receipt.get('source_sha256')==spec['sha256']['subject.py']
                and receipt.get('tests_sha256')==spec['sha256']['tests/test_regression.py']
                and receipt.get('candidate_sha256')==digest(receipt['candidate'].encode())
                and receipt.get('proposal_sha256')==digest(raw) and receipt.get('image')==IMAGE
                and receipt.get('outcome')=='VERIFIED' and receipt.get('independently_verified') is True
                and receipt.get('state')=='AWAITING_OWNER_APPROVAL'
                and all(row.get('passed') is True and row.get('exit_code')==0
                        and type(row.get('tests_run')) is int and row['tests_run']>0 for row in observations)
                and all(receipt.get(key) is False for key in ('paid_fallback','delivery_authorized',
                    'customer_execution_authorized','independent_evaluation')))
    except (ValueError,KeyError,TypeError,AttributeError,StopIteration):return False


class OwnedRepairQueue:
    def __init__(self, path=DEFAULT_PATH, *, service_factory=RepairService, clock=time.time):
        self.path=Path(path); self.factory=service_factory; self.clock=clock; self.sessions={}
        if not self.path.is_absolute():raise RepairRejected('QUEUE_ABSOLUTE_PATH_REQUIRED')
        try:
            self.path.parent.mkdir(mode=0o700, exist_ok=True)
            for parent in self.path.parents:
                if parent.is_symlink():raise RepairRejected('QUEUE_SYMLINK_PARENT')
            try:fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
            except FileExistsError:fd=os.open(self.path,os.O_RDWR|os.O_NOFOLLOW)
            os.close(fd)
            with self._db() as db:
                db.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, engine TEXT, '
                           'cases TEXT, stopped INTEGER NOT NULL DEFAULT 0, created REAL)')
                db.execute('CREATE TABLE IF NOT EXISTS owned_jobs (id TEXT PRIMARY KEY, batch TEXT, '
                           'case_id TEXT, state TEXT, claims INTEGER NOT NULL DEFAULT 0, '
                           'attempts INTEGER NOT NULL DEFAULT 0, token TEXT, expires REAL, '
                           'deadline REAL, proposals TEXT NOT NULL DEFAULT \'[]\', receipt TEXT, '
                           'outcome TEXT)')
        except (OSError,sqlite3.Error):raise RepairRejected('OWNED_QUEUE_UNAVAILABLE') from None

    @contextmanager
    def _db(self):
        for path, directory in ((self.path.parent,True),(self.path,False)):
            info=path.lstat()
            if (info.st_uid!=os.getuid() or info.st_mode & 0o077
                    or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                    or (not directory and (info.st_nlink!=1 or info.st_size>2_000_000))):
                raise RepairRejected('OWNED_QUEUE_PRIVACY_OR_SIZE_REJECTED')
        db=sqlite3.connect(self.path,timeout=2,isolation_level=None)
        db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.execute('COMMIT')
        except BaseException:
            db.rollback();raise
        finally:db.close()

    @staticmethod
    def _id(value):
        if type(value) is not str or not re.fullmatch('[a-zA-Z0-9_-]{1,48}',value):
            raise RepairRejected('INVALID_OWNED_QUEUE_ID')

    def _batch(self,db,batch_id):
        self._id(batch_id)
        row=db.execute('SELECT * FROM batches WHERE id=?',(batch_id,)).fetchone()
        if row is None:raise RepairRejected('UNKNOWN_OWNED_BATCH')
        return row

    def create(self,batch_id,engine,case_ids):
        self._id(batch_id)
        allowed={item['id'] for item in catalog()}
        if (engine not in ENGINES or type(case_ids) is not list or not 1<=len(case_ids)<=5
                or any(type(x) is not str or x not in allowed for x in case_ids)
                or len(set(case_ids))!=len(case_ids)):
            raise RepairRejected('OWNED_BATCH_SCOPE_REJECTED')
        cases=encoded(case_ids).decode()
        with self._db() as db:
            prior=db.execute('SELECT * FROM batches WHERE id=?',(batch_id,)).fetchone()
            if prior:
                if (prior['engine'],prior['cases'])!=(engine,cases):raise RepairRejected('BATCH_ID_CONFLICT')
                return {'batch_id':batch_id,'created':False}
            if db.execute('SELECT COUNT(*) FROM batches').fetchone()[0]>=4:
                raise RepairRejected('QUEUE_BATCH_BUDGET_EXHAUSTED')
            db.execute('INSERT INTO batches(id,engine,cases,created) VALUES(?,?,?,?)',
                       (batch_id,engine,cases,self.clock()))
            for case_id in case_ids:
                db.execute('INSERT INTO owned_jobs(id,batch,case_id,state) VALUES(?,?,?,?)',
                           (uuid.uuid4().hex,batch_id,case_id,'QUEUED'))
        return {'batch_id':batch_id,'created':True,'engine':engine,'jobs':len(case_ids)}

    def _expire(self,db):
        now=self.clock()
        db.execute("UPDATE owned_jobs SET state=CASE WHEN claims>=? OR attempts>=? OR deadline<=? "
                   "THEN 'FAILED' ELSE 'QUEUED' END,token=NULL,expires=NULL,outcome='LEASE_EXPIRED' "
                   "WHERE state IN ('LEASED','VERIFYING') AND expires<=?",(MAX_CLAIMS,MAX_ATTEMPTS,now,now))

    def claim(self,batch_id):
        with self._db() as db:
            batch=self._batch(db,batch_id);self._expire(db)
            if batch['stopped']:return {'outcome':'STOPPED','batch_id':batch_id}
            if self.clock()-batch['created']>1800:return {'outcome':'BATCH_TIME_BUDGET_EXHAUSTED'}
            if db.execute("SELECT 1 FROM owned_jobs WHERE state IN ('LEASED','VERIFYING')").fetchone():
                return {'outcome':'WORKER_BUSY'}
            row=db.execute("SELECT * FROM owned_jobs WHERE batch=? AND state='QUEUED' ORDER BY rowid LIMIT 1",(batch_id,)).fetchone()
            if not row:return {'outcome':'QUEUE_COMPLETE','batch_id':batch_id}
            token=uuid.uuid4().hex;deadline=row['deadline'] or self.clock()+JOB_SECONDS
            db.execute("UPDATE owned_jobs SET state='LEASED',claims=claims+1,token=?,expires=?,deadline=? WHERE id=?",
                       (token,min(self.clock()+LEASE_SECONDS,deadline),deadline,row['id']))
        service=self.factory()
        try:task=service.prepare(row['case_id'],batch['engine'])
        except (ValueError,RuntimeError,OSError) as exc:
            outcome=(str(exc) if isinstance(exc,RepairUnavailable) and str(exc) in {
                'SANDBOX_ADMISSION_UNAVAILABLE','BASELINE_OBSERVATION_UNAVAILABLE'}
                else 'OWNED_PREPARATION_REJECTED' if isinstance(exc,ValueError) else 'PREPARATION_WORKER_ERROR')
            with self._db() as db:
                db.execute("UPDATE owned_jobs SET state='BLOCKED',outcome=?,token=NULL,expires=NULL WHERE id=? AND token=?",
                           (outcome,row['id'],token))
            return {'job_id':row['id'],'state':'BLOCKED','outcome':outcome}
        with self._db() as db:self._fence(db,batch_id,row['id'],token)
        self.sessions[row['id']]={'service':service,'task':task,'token':token}
        return {'job_id':row['id'],'batch_id':batch_id,'lease_token':token,'lease_seconds':LEASE_SECONDS,
                'attempts_used':row['attempts'],'attempts_remaining':MAX_ATTEMPTS-row['attempts'],
                'previous_receipt':strict_json(row['receipt']) if row['receipt'] else None,'task':task}

    def _fence(self,db,batch_id,job_id,lease_token):
        batch=self._batch(db,batch_id)
        row=db.execute('SELECT * FROM owned_jobs WHERE id=? AND batch=?',(job_id,batch_id)).fetchone()
        if (batch['stopped'] or row is None or row['token']!=lease_token
                or row['state'] not in ('LEASED','VERIFYING') or row['expires']<=self.clock()
                or row['deadline']<=self.clock()):raise RepairRejected('STALE_EXPIRED_OR_REVOKED_LEASE')
        return row

    def heartbeat(self,batch_id,job_id,lease_token):
        with self._db() as db:
            row=self._fence(db,batch_id,job_id,lease_token)
            expires=min(self.clock()+LEASE_SECONDS,row['deadline'])
            db.execute('UPDATE owned_jobs SET expires=? WHERE id=?',(expires,job_id))
        return {'outcome':'LEASE_RENEWED','lease_seconds':max(0,int(expires-self.clock()))}

    def release(self,batch_id,job_id,lease_token):
        with self._db() as db:
            row=self._fence(db,batch_id,job_id,lease_token)
            state='FAILED' if row['claims']>=MAX_CLAIMS or row['attempts']>=MAX_ATTEMPTS else 'QUEUED'
            db.execute('UPDATE owned_jobs SET state=?,token=NULL,expires=NULL,outcome=? WHERE id=?',
                       (state,'SESSION_RELEASED',job_id))
        self.sessions.pop(job_id,None)
        return {'state':state,'outcome':'SESSION_RELEASED'}

    def _reserve(self,batch_id,job_id,lease_token,proposal=None,qwen=False):
        with self._db() as db:
            row=self._fence(db,batch_id,job_id,lease_token)
            if row['state']!='LEASED':raise RepairRejected('VERIFICATION_IN_PROGRESS')
            session=self.sessions.get(job_id)
            if not session or session['token']!=lease_token:raise RepairRejected('SESSION_CAPABILITY_LOST')
            required=2 if qwen else 1
            if row['attempts']+required>MAX_ATTEMPTS:raise RepairRejected('QUEUE_ATTEMPT_BUDGET_EXHAUSTED')
            hashes=strict_json(row['proposals'])
            if proposal is not None:
                raw=encoded(proposal)
                if len(raw)>3000:raise RepairRejected('PROPOSAL_BUDGET_EXCEEDED')
                sha=digest(raw)
                if sha in hashes:raise RepairRejected('REPEATED_PROPOSAL_AFTER_RECOVERY')
                hashes.append(sha)
            db.execute("UPDATE owned_jobs SET state='VERIFYING',attempts=attempts+?,proposals=? WHERE id=?",
                       (required,encoded(hashes).decode(),job_id))
        return session

    def _finish(self,batch_id,job_id,lease_token,result):
        receipt=result.get('verification_receipt',result)
        task=self.sessions[job_id]['task']
        claimed=(receipt.get('independently_verified') is True or receipt.get('outcome')=='VERIFIED')
        verified=claimed and valid_success(receipt,task['case_id'],task['engine'],task['task_id'])
        if claimed and not verified:
            result={'state':'BLOCKED','outcome':'VERIFICATION_RECEIPT_INVALID','independently_verified':False,
                    'rejected_result_sha256':digest(encoded(result))}
            receipt=result
        with self._db() as db:
            try:row=self._fence(db,batch_id,job_id,lease_token)
            except RepairRejected:return {'outcome':'LEASE_REVOKED_RESULT_DISCARDED','state':'STOPPED_OR_EXPIRED'}
            state=('VERIFIED' if verified else 'BLOCKED' if result.get('state')=='BLOCKED'
                   else 'FAILED' if row['attempts']>=MAX_ATTEMPTS or receipt.get('state')=='EXHAUSTED' else 'LEASED')
            raw=encoded(result).decode()
            if len(raw.encode())>100000:raise RepairRejected('QUEUE_RESULT_BUDGET_EXCEEDED')
            db.execute('UPDATE owned_jobs SET state=?,receipt=?,outcome=?,token=?,expires=? WHERE id=?',
                       (state,raw,result.get('outcome'),lease_token if state=='LEASED' else None,
                        row['expires'] if state=='LEASED' else None,job_id))
        if state!='LEASED':self.sessions.pop(job_id,None)
        return {'job_id':job_id,'state':state,'attempts_used':row['attempts'],'receipt':result,
                'independent_evaluation':False,'delivery_authorized':False}

    def submit(self,batch_id,job_id,lease_token,revision,proposal):
        # Validate session revision before reserving durable execution budget.
        session=self.sessions.get(job_id)
        if not session:raise RepairRejected('SESSION_CAPABILITY_LOST')
        task=session['task']
        if task['engine']!='CODEX_AGENT':raise RepairRejected('QUEUE_ENGINE_MISMATCH')
        if type(revision) is not int or revision!=task['revision']:raise RepairRejected('STALE_REVISION')
        session=self._reserve(batch_id,job_id,lease_token,proposal)
        try:result=session['service'].submit(task['task_id'],revision,proposal)
        except (RuntimeError,OSError,ValueError):
            return self._finish(batch_id,job_id,lease_token,
                                {'state':'BLOCKED','outcome':'WORKER_ERROR','independently_verified':False})
        task['revision']=result.get('revision',revision)
        return self._finish(batch_id,job_id,lease_token,result)

    def run_qwen(self,batch_id,job_id,lease_token):
        session=self.sessions.get(job_id)
        if not session or session['task']['engine']!='QWEN_LOCAL':raise RepairRejected('QUEUE_ENGINE_MISMATCH')
        session=self._reserve(batch_id,job_id,lease_token,qwen=True)
        task=session['task']
        try:result=session['service'].run_qwen(task['task_id'],0)
        except (RuntimeError,OSError,ValueError):
            result={'state':'BLOCKED','outcome':'WORKER_ERROR','independently_verified':False}
        return self._finish(batch_id,job_id,lease_token,result)

    def stop(self,batch_id):
        with self._db() as db:
            self._batch(db,batch_id)
            db.execute('UPDATE batches SET stopped=1 WHERE id=?',(batch_id,))
            db.execute("UPDATE owned_jobs SET state='STOPPED',token=NULL,expires=NULL,outcome='OWNER_STOP' "
                       "WHERE batch=? AND state IN ('QUEUED','LEASED','VERIFYING')",(batch_id,))
        return {'batch_id':batch_id,'outcome':'STOPPED','in_flight_behavior':'already-started bounded verification may finish; result discarded'}

    def status(self,batch_id):
        with self._db() as db:
            batch=self._batch(db,batch_id);self._expire(db)
            jobs=[dict(row) for row in db.execute('SELECT id,case_id,state,claims,attempts,outcome,receipt FROM owned_jobs WHERE batch=? ORDER BY rowid',(batch_id,))]
        for job in jobs:
            raw=job.pop('receipt')
            if job['state']=='VERIFIED':
                value=strict_json(raw) if raw else {}
                if not valid_success(value.get('verification_receipt',value),job['case_id'],batch['engine']):
                    raise RepairRejected('QUEUE_RECEIPT_CORRUPT')
            job['receipt_sha256']=digest(raw.encode()) if raw else None
        return {'batch_id':batch_id,'engine':batch['engine'],'stopped':bool(batch['stopped']),
                'jobs':jobs,'active_session_required':batch['engine']=='CODEX_AGENT',
                'cross_cloud_session_storage_verified':False,'independent_evaluation':False,
                'paid_fallback':False,'customer_execution_authorized':False,'delivery_authorized':False}
