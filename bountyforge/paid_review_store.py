"""Private-volume SQLite CAS for review records only; never an execution queue.

No production volume is configured. An ephemeral Actions workspace is NOT a
durable deployment of this adapter. Never place customer/payment state in the
public synthetic ledger, artifacts, model context or repository.
"""
from __future__ import annotations
import json
import os
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from bountyforge.paid_review_ledger import ReviewLedgerRejected, _validate_state

MAX_STATE_BYTES = 65536


class SQLitePaidReviewStore:
    """Trusted coordinator only, at an explicitly approved private volume path."""
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.is_absolute():
            raise ReviewLedgerRejected('Private store requires an absolute configured path')
        if self.path.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise ReviewLedgerRejected('Private payment state must remain outside the source checkout')
        try:
            parent = self.path.parent.lstat()
            if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                    or parent.st_mode & 0o077):
                raise ReviewLedgerRejected('Store directory must be private to the coordinator')
            try:
                fd = os.open(self.path, os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                fd = os.open(self.path, os.O_RDWR|os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_nlink != 1 or info.st_mode & 0o077):
                    raise ReviewLedgerRejected('Store file must be private and unlinked')
            finally:
                os.close(fd)
            with closing(self._connect()) as conn:
                conn.execute('CREATE TABLE IF NOT EXISTS paid_review_state '
                             '(singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
                             'revision INTEGER NOT NULL CHECK(revision>0), payload TEXT NOT NULL)')
                conn.commit()
        except (OSError, sqlite3.Error):
            raise ReviewLedgerRejected('Private paid-review store unavailable') from None

    def _connect(self):
        conn = None
        try:
            self._verify_privacy()
            conn = sqlite3.connect(self.path, timeout=2)
            conn.execute('PRAGMA synchronous=FULL')
            return conn
        except sqlite3.Error:
            if conn is not None: conn.close()
            raise ReviewLedgerRejected('Private paid-review connection unavailable') from None

    def _verify_privacy(self):
        try:
            parent=self.path.parent.lstat()
            if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                    or parent.st_mode & 0o077):
                raise ReviewLedgerRejected('Private store directory changed')
            fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW)
            try:
                info=os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_nlink != 1 or info.st_mode & 0o077):
                    raise ReviewLedgerRejected('Private store file changed')
            finally:os.close(fd)
        except OSError:
            raise ReviewLedgerRejected('Private store path unavailable') from None

    def read(self):
        try:
            with closing(self._connect()) as conn:
                row = conn.execute('SELECT revision,payload FROM paid_review_state WHERE singleton=1').fetchone()
            if row is None:
                return None, None
            revision, raw = row
            if type(revision) is not int or revision < 1 or len(raw.encode()) > MAX_STATE_BYTES:
                raise ReviewLedgerRejected('Corrupt paid-review state')
            state = json.loads(raw)
            _validate_state(state)
            return state, str(revision)
        except (sqlite3.Error, ValueError, TypeError, AttributeError):
            raise ReviewLedgerRejected('Private paid-review read rejected') from None

    def write(self, state, expected_version):
        _validate_state(state)
        raw = json.dumps(state, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(raw.encode()) > MAX_STATE_BYTES:
            raise ReviewLedgerRejected('Paid-review state exceeds budget')
        if expected_version is not None and (not isinstance(expected_version, str)
                or not expected_version.isascii() or not expected_version.isdecimal()
                or not 1 <= len(expected_version) <= 18 or int(expected_version) < 1):
            raise ReviewLedgerRejected('Invalid paid-review CAS revision')
        conn = self._connect()
        try:
            # Serialize comparison and replacement under the same database lock.
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT revision FROM paid_review_state WHERE singleton=1').fetchone()
            actual = str(row[0]) if row else None
            if actual != expected_version:
                raise ReviewLedgerRejected('Paid-review CAS conflict')
            revision = int(actual)+1 if actual else 1
            if row:
                conn.execute('UPDATE paid_review_state SET revision=?,payload=? WHERE singleton=1', (revision,raw))
            else:
                conn.execute('INSERT INTO paid_review_state VALUES (1,?,?)', (revision,raw))
            conn.commit()
            return str(revision)
        except sqlite3.Error:
            raise ReviewLedgerRejected('Private paid-review write rejected') from None
        finally:
            cleanup_failed=False
            try:
                conn.rollback()
            except sqlite3.Error:
                cleanup_failed=True
            finally:
                try:conn.close()
                except sqlite3.Error:cleanup_failed=True
            if cleanup_failed:
                raise ReviewLedgerRejected('Private paid-review cleanup failed') from None
