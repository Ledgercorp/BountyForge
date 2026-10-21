"""Private metadata-only scope review; never an executable customer-job queue.

An owner-controlled HMAC key authenticates exact scope metadata. No key, source,
customer identity, provider operation or delivery capability is stored/accepted.
Existing payment reviews are historical evidence, not fresh fulfillment proof.
"""
from __future__ import annotations
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import stat
from contextlib import closing
from pathlib import Path

from bountyforge.drafts import safe_path
from bountyforge.paid_review_ledger import ReviewLedgerRejected, _validate_state as validate_reviews
from bountyforge.paid_review_store import SQLitePaidReviewStore

HEX = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[0-9a-f]{32}\Z')
HOLDS = {'cancelled', 'refund_or_dispute', 'owner_revoked', 'repair_failed'}
MAX_PLANS, MAX_EVENTS, MAX_BYTES = 100, 32, 262144
PAYLOAD_FIELDS = {'schema', 'session_sha256', 'source_path', 'source_sha256', 'tests_sha256',
                  'test_path', 'dependency_policy', 'source_access_receipt_sha256',
                  'model_sharing_receipt_sha256', 'owner_approval_id', 'expires_at'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def _integer(value):
    return type(value) is int and 0 <= value < 2**53


def _approval_shape(approval):
    if (not isinstance(approval, dict) or set(approval) != {'payload', 'signature'}
            or not isinstance(approval['signature'], str) or not HEX.fullmatch(approval['signature'])):
        raise ReviewLedgerRejected('Unrecognized owner scope approval')
    payload = approval['payload']
    if (not isinstance(payload, dict) or set(payload) != PAYLOAD_FIELDS
            or type(payload['schema']) is not int or payload['schema'] != 1
            or not isinstance(payload['owner_approval_id'], str)
            or not ID.fullmatch(payload['owner_approval_id'])
            or not _integer(payload['expires_at'])
            or payload['test_path'] != 'tests/test_regression.py'
            or payload['dependency_policy'] != 'stdlib_only_v1'):
        raise ReviewLedgerRejected('Owner scope profile unsupported')
    for field in ('session_sha256', 'source_sha256', 'tests_sha256',
                  'source_access_receipt_sha256', 'model_sharing_receipt_sha256'):
        if not isinstance(payload[field], str) or not HEX.fullmatch(payload[field]):
            raise ReviewLedgerRejected('Owner scope hashes missing')
    try:
        path = safe_path(payload['source_path'])
    except (TypeError, ValueError):
        raise ReviewLedgerRejected('Owner source path rejected') from None
    if (not path.endswith('.py') or 'tests' in Path(path).parts
            or Path(path).name.startswith('test_') or Path(path).name.endswith('_test.py')):
        raise ReviewLedgerRejected('Owner source path rejected')
    return payload


def validate_scope_state(state):
    if (not isinstance(state, dict) or set(state) != {'version', 'plans'}
            or type(state['version']) is not int or state['version'] != 1
            or not isinstance(state['plans'], list) or len(state['plans']) > MAX_PLANS):
        raise ReviewLedgerRejected('Unrecognized scope-review state')
    seen = set()
    for plan in state['plans']:
        if (not isinstance(plan, dict) or set(plan) != {'session_sha256', 'approval', 'scope_sha256',
                'state', 'fence', 'lease', 'hold_reasons', 'events'}):
            raise ReviewLedgerRejected('Invalid scope-review plan')
        payload = _approval_shape(plan['approval'])
        if (plan['session_sha256'] != payload['session_sha256'] or plan['session_sha256'] in seen
                or plan['scope_sha256'] != hashlib.sha256(_canonical(payload)).hexdigest()
                or not _integer(plan['fence']) or plan['fence'] < 1
                or not isinstance(plan['hold_reasons'], list)
                or any(reason not in HOLDS for reason in plan['hold_reasons'])
                or plan['hold_reasons'] != sorted(set(plan['hold_reasons']))
                or plan['state'] != ('blocked' if plan['hold_reasons'] else 'awaiting_private_execution_admission')):
            raise ReviewLedgerRejected('Scope-review binding or state invalid')
        lease = plan['lease']
        if lease is not None and (not isinstance(lease, dict) or set(lease) != {'token_sha256', 'expires_at'}
                or not isinstance(lease['token_sha256'], str) or not HEX.fullmatch(lease['token_sha256'])
                or not _integer(lease['expires_at']) or plan['hold_reasons']):
            raise ReviewLedgerRejected('Invalid scope-review lease')
        events = plan['events']
        if (not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS
                or len(events) != plan['fence']):
            raise ReviewLedgerRejected('Scope-review history incomplete')
        for number, event in enumerate(events, 1):
            if (not isinstance(event, dict) or set(event) != {'kind', 'at', 'fence'}
                    or event['kind'] not in {'scope_recorded', 'review_claimed', 'lease_recovered',
                                            'review_released'} | HOLDS
                    or not _integer(event['at']) or event['fence'] != number):
                raise ReviewLedgerRejected('Invalid scope-review event')
        seen.add(plan['session_sha256'])


class SQLiteScopeReviewStore(SQLitePaidReviewStore):
    """Dedicated private database; reuses existing connection/privacy controls."""
    def __init__(self, path):
        self.path = Path(path)
        if (not self.path.is_absolute()
                or self.path.resolve().is_relative_to(Path(__file__).resolve().parents[1])):
            raise ReviewLedgerRejected('Scope-review database must be private and outside checkout')
        try:
            parent = self.path.parent.lstat()
            if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
                raise ReviewLedgerRejected('Scope-review directory not private')
            fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            self._verify_privacy()
            with closing(self._connect()) as conn:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables - {'scope_review_state'}:
                    raise ReviewLedgerRejected('Dedicated scope-review database required')
                conn.execute('CREATE TABLE IF NOT EXISTS scope_review_state '
                             '(singleton INTEGER PRIMARY KEY CHECK(singleton=1), '
                             'revision INTEGER NOT NULL CHECK(revision>0), payload TEXT NOT NULL)')
                conn.commit()
        except (OSError, sqlite3.Error):
            raise ReviewLedgerRejected('Private scope-review store unavailable') from None

    def read(self):
        try:
            with closing(self._connect()) as conn:
                row = conn.execute('SELECT revision,payload FROM scope_review_state WHERE singleton=1').fetchone()
            if row is None:
                return None, None
            revision, raw = row
            if type(revision) is not int or revision < 1 or len(raw.encode()) > MAX_BYTES:
                raise ValueError('Invalid private state')
            state = json.loads(raw)
            validate_scope_state(state)
            return state, str(revision)
        except (sqlite3.Error, ValueError, TypeError, AttributeError):
            raise ReviewLedgerRejected('Private scope-review read rejected') from None

    def write(self, state, expected_version):
        validate_scope_state(state)
        raw = _canonical(state)
        if len(raw) > MAX_BYTES or (expected_version is not None and
                (not isinstance(expected_version, str) or not expected_version.isascii()
                 or not expected_version.isdecimal() or not 1 <= len(expected_version) <= 18
                 or str(int(expected_version)) != expected_version or int(expected_version) < 1)):
            raise ReviewLedgerRejected('Scope-review state or revision exceeds bounds')
        conn = self._connect()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT revision FROM scope_review_state WHERE singleton=1').fetchone()
            actual = str(row[0]) if row else None
            if actual != expected_version:
                raise ReviewLedgerRejected('Scope-review CAS conflict')
            revision = int(actual) + 1 if actual else 1
            conn.execute('INSERT OR REPLACE INTO scope_review_state VALUES (1,?,?)',
                         (revision, raw.decode('ascii')))
            conn.commit()
            return str(revision)
        except sqlite3.Error:
            raise ReviewLedgerRejected('Private scope-review write rejected') from None
        finally:
            try:
                conn.rollback()
            finally:
                conn.close()


class PaidScopeReview:
    """Trusted coordinator only. All success responses still prohibit execution."""
    def __init__(self, store, payment_review_store, *, approval_key):
        if (type(store) is not SQLiteScopeReviewStore or type(payment_review_store) is not SQLitePaidReviewStore
                or not isinstance(approval_key, bytes) or not 32 <= len(approval_key) <= 64):
            raise ReviewLedgerRejected('Trusted private stores and owner approval verifier required')
        self.store, self.payment_reviews, self._key = store, payment_review_store, approval_key

    def _read(self):
        state, revision = self.store.read()
        if state is None:
            if revision is not None: raise ReviewLedgerRejected('Invalid empty revision')
            state = {'version': 1, 'plans': []}
        elif revision is None:
            raise ReviewLedgerRejected('Scope state lacks CAS revision')
        validate_scope_state(state)
        return copy.deepcopy(state), revision

    @staticmethod
    def _plan(state, session):
        found = [plan for plan in state['plans'] if plan['session_sha256'] == session]
        if len(found) != 1: raise ReviewLedgerRejected('Scope-review plan not found')
        return found[0]

    @staticmethod
    def _result(plan, status='recorded'):
        return {'status': status, 'session_sha256': plan['session_sha256'], 'state': plan['state'],
                'fence': plan['fence'], 'execution_authorized': False, 'delivery_authorized': False,
                'source_accepted': False, 'payment_freshly_verified': False}

    @staticmethod
    def _event(plan, kind, now):
        limit = MAX_EVENTS if kind in HOLDS else MAX_EVENTS - len(HOLDS)
        if not _integer(now) or len(plan['events']) >= limit:
            raise ReviewLedgerRejected('Scope-review time or event budget invalid')
        plan['fence'] += 1
        plan['events'].append({'kind': kind, 'at': now, 'fence': plan['fence']})

    def record_scope(self, session, approval, *, now):
        payload = _approval_shape(approval)
        if (not _integer(now) or not now < payload['expires_at'] <= now + 30 * 86400
                or payload['session_sha256'] != session
                or not hmac.compare_digest(approval['signature'],
                    hmac.new(self._key, _canonical(payload), hashlib.sha256).hexdigest())):
            raise ReviewLedgerRejected('Owner scope signature, binding or expiry rejected')
        reviews, _ = self.payment_reviews.read()
        validate_reviews(reviews)
        if not any(entry['session_sha256'] == session for entry in reviews['orders']):
            raise ReviewLedgerRejected('No prior independently verified payment review')
        state, revision = self._read()
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        existing = [p for p in state['plans'] if p['session_sha256'] == session]
        if existing:
            if existing[0]['scope_sha256'] != digest:
                raise ReviewLedgerRejected('Conflicting approved scope for same payment')
            return self._result(existing[0], 'already_recorded')
        if len(state['plans']) >= MAX_PLANS: raise ReviewLedgerRejected('Scope-review capacity exhausted')
        plan = {'session_sha256': session, 'approval': copy.deepcopy(approval), 'scope_sha256': digest,
                'state': 'awaiting_private_execution_admission', 'fence': 0, 'lease': None,
                'hold_reasons': [], 'events': []}
        self._event(plan, 'scope_recorded', now)
        state['plans'].append(plan); self.store.write(state, revision)
        return self._result(plan)

    def claim_review(self, session, *, expected_fence, now, ttl=60):
        if type(ttl) is not int or not 1 <= ttl <= 300 or not _integer(now):
            raise ReviewLedgerRejected('Review lease budget invalid')
        state, revision = self._read(); plan = self._plan(state, session)
        approved = plan['approval']
        if not hmac.compare_digest(approved['signature'],
                hmac.new(self._key, _canonical(approved['payload']), hashlib.sha256).hexdigest()):
            raise ReviewLedgerRejected('Cached owner scope signature rejected')
        if (type(expected_fence) is not int or expected_fence != plan['fence'] or plan['hold_reasons']
                or now >= plan['approval']['payload']['expires_at']
                or any(p['lease'] and p['lease']['expires_at'] > now for p in state['plans'])):
            raise ReviewLedgerRejected('Review claim unavailable or stale')
        recovered = plan['lease'] is not None
        token = secrets.token_hex(16)
        self._event(plan, 'lease_recovered' if recovered else 'review_claimed', now)
        plan['lease'] = {'token_sha256': hashlib.sha256(token.encode()).hexdigest(),
                         'expires_at': min(now + ttl, plan['approval']['payload']['expires_at'])}
        self.store.write(state, revision)
        return {**self._result(plan), 'token': token, 'lease_expires_at': plan['lease']['expires_at']}

    def release_review(self, session, *, token, fence, now):
        state, revision = self._read(); plan = self._plan(state, session); lease = plan['lease']
        if (not _integer(now) or type(fence) is not int or plan['fence'] != fence
                or not isinstance(token, str) or not ID.fullmatch(token) or lease is None
                or lease['expires_at'] <= now
                or not hmac.compare_digest(lease['token_sha256'], hashlib.sha256(token.encode()).hexdigest())):
            raise ReviewLedgerRejected('Stale or invalid review claim')
        self._event(plan, 'review_released', now); plan['lease'] = None
        self.store.write(state, revision)
        return self._result(plan)

    def hold(self, session, *, reason, now):
        if reason not in HOLDS: raise ReviewLedgerRejected('Unknown blocking event')
        state, revision = self._read(); plan = self._plan(state, session)
        if reason in plan['hold_reasons']: return self._result(plan, 'already_recorded')
        self._event(plan, reason, now)
        plan['state'] = 'blocked'; plan['lease'] = None
        plan['hold_reasons'] = sorted(plan['hold_reasons'] + [reason])
        self.store.write(state, revision)
        return self._result(plan)

    def delivery_review(self, session, *, now):
        if not _integer(now): raise ReviewLedgerRejected('Invalid review time')
        state, _ = self._read(); plan = self._plan(state, session)
        blockers = ['private_execution_unadmitted', 'source_hashes_not_matched_to_private_source',
                    'fresh_payment_evidence_required', 'independent_private_repair_verification_absent',
                    'specific_owner_delivery_approval_required']
        if now >= plan['approval']['payload']['expires_at']: blockers.append('scope_approval_expired')
        return {**self._result(plan, 'delivery_blocked'), 'blockers': blockers,
                'hold_reasons': list(plan['hold_reasons'])}
