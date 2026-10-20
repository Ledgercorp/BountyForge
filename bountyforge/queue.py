"""SQLite-backed bounded task coordination with expired-lease recovery."""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = '''CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, state TEXT NOT NULL CHECK(state IN ('queued','running','review_ready','failed')),
 created REAL NOT NULL, updated REAL NOT NULL, lease_until REAL, attempts INTEGER NOT NULL DEFAULT 0,
 input_json TEXT NOT NULL, result_json TEXT
)'''

class Queue:
    def __init__(self, dbfile: Path):
        self.conn = sqlite3.connect(str(dbfile), timeout=5, isolation_level=None)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA busy_timeout=5000')
        self.conn.execute(SCHEMA)

    def enqueue(self, job_id: str, data: dict) -> bool:
        if not job_id or len(job_id) > 120 or not job_id.replace('-', '').replace('_','').isalnum():
            raise ValueError('invalid job id')
        stamp = time.time()
        res = self.conn.execute('INSERT OR IGNORE INTO jobs(id,state,created,updated,input_json) VALUES(?,?,?,?,?)',
                                (job_id,'queued',stamp,stamp,json.dumps(data)))
        return res.rowcount == 1

    def claim(self, lease_seconds: int = 60) -> dict | None:
        if not 5 <= lease_seconds <= 900:
            raise ValueError('Invalid lease duration')
        now = time.time()
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            # Exhausted interrupted jobs must become terminal failures.
            self.conn.execute("UPDATE jobs SET state='failed',result_json=?,lease_until=NULL,updated=? WHERE state='running' AND lease_until<? AND attempts>=2",
                              (json.dumps({'status':'failed','error':'lease_exhausted'}),now,now))
            row = self.conn.execute("SELECT id,input_json,attempts FROM jobs WHERE state='queued' OR (state='running' AND lease_until<? AND attempts<2) ORDER BY created LIMIT 1",(now,)).fetchone()
            if row is None:
                self.conn.execute('COMMIT'); return None
            self.conn.execute("UPDATE jobs SET state='running',attempts=attempts+1,lease_until=?,updated=? WHERE id=?",(now+lease_seconds,now,row[0]))
            self.conn.execute('COMMIT')
            return {'id':row[0], 'input':json.loads(row[1]), 'attempts':row[2]+1}
        except BaseException:
            self.conn.execute('ROLLBACK'); raise

    def finish(self, job_id: str, result: dict) -> bool:
        status = result.get('status')
        if status not in ('failed','review_ready'):
            raise ValueError('Only verified terminal statuses are permitted')
        response = self.conn.execute('UPDATE jobs SET state=?,result_json=?,lease_until=NULL,updated=? WHERE id=? AND state=\'running\'',
                                     (status,json.dumps(result),time.time(),job_id))
        return response.rowcount == 1

    def get(self, job_id: str) -> dict | None:
        row=self.conn.execute('SELECT state,attempts,result_json FROM jobs WHERE id=?',(job_id,)).fetchone()
        return None if row is None else {'state':row[0], 'attempts':row[1], 'result':json.loads(row[2]) if row[2] else None}

    def close(self): self.conn.close()