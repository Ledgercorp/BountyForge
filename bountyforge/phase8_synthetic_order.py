"""NONPRODUCTION order simulation: owned bytes, loopback provider, no credentials.

This does not admit a real paid order into production payment/scope journals.
StripeOrderGate's validation logic is reused only by a fixed simulator subclass;
its exact-type production ledger admission guards are deliberately preserved.
"""
from __future__ import annotations
import fcntl
import http.client
import json
import os
import secrets
import select
import sqlite3
import stat
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from bountyforge.phase7_owned_demo import (OwnedOnlyLedger, SOURCE, PATCHED, SOURCE_HASH,
    PATCHED_HASH, canonical, digest, package_record, replay, require_private_directory,
    SyntheticBlocked)
from bountyforge.stripe_order_gate import StripeOrderGate, OrderNotVerified

SESSION = 'cs_live_BountyForgeSIMULATIONONLY0001'
PAYMENT = 'pi_BountyForgeSIMULATIONONLY0001'
CHARGE = 'ch_BountyForgeSIMULATIONONLY0001'
LINK = 'plink_BountyForgeSIMULATIONONLY0001'
JOB = 'synthetic_0123456789abcdef'
MARKER = '.phase8-SIMULATION_ONLY'
IDENTITY = b'BountyForge Phase8 OWNED PROVIDER SIMULATOR ONLY v1\n'
DATABASE = 'phase8.SIMULATION_ONLY.sqlite3'
PACKAGE = 'phase8.SIMULATION_ONLY.review.json'
PROOF = 'phase8.SIMULATION_ONLY.verification.json'
SCENARIOS = ('paid', 'unpaid', 'underpaid', 'cancelled', 'disputed', 'refunded',
             'replay', 'invalid_session')
ALLOWED = {MARKER, DATABASE, DATABASE+'-journal', 'phase8.SIMULATION_ONLY.lock',
           PACKAGE, PROOF, JOB+'.review.json'}


class SimulationRejected(ValueError):
    pass


def result(**values):
    return dict(kind='phase8_owned_order_simulation', provider_simulator=True,
        stripe_test_mode_verified=False, real_payment_verified=False,
        delivery_authorized=False, private_execution_authorized=False,
        customer_source_accepted=False, owner_consent_verified=False,
        customer_rights_verified=False, model_calls=0, received_revenue_usd=0,
        owned_fulfillment_started=False, provider_requests=0,
        independent_owned_replays=0, **values)


def _private_read(path, limit=8192):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or info.st_mode & 0o077):
                raise SimulationRejected('workspace_rejected')
            raw = os.read(fd, limit + 1)
        finally:
            os.close(fd)
        if len(raw) > limit: raise SimulationRejected('workspace_rejected')
        return raw
    except OSError:
        raise SimulationRejected('workspace_rejected') from None


def _write_exact(path, raw):
    if path.exists() or path.is_symlink():
        if _private_read(path) != raw: raise SimulationRejected('package_tampered')
        return
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            remaining = raw
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0: raise SimulationRejected('workspace_rejected')
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    except OSError:
        raise SimulationRejected('workspace_rejected') from None


def initialize(root):
    root = require_private_directory(Path(root))
    if list(root.iterdir()): raise SimulationRejected('workspace_not_empty')
    _write_exact(root / MARKER, IDENTITY)
    return result(status='initialized', state='SIMULATION_ONLY')


def _records(scenario):
    session = dict(id=SESSION, livemode=True, mode='payment', status='complete',
        payment_status='paid', currency='usd', amount_total=4900, payment_intent=PAYMENT,
        payment_link=LINK, metadata={'bountyforge_service':'python_bugfix_basic', 'contract_version':'1'})
    payment = dict(id=PAYMENT, livemode=True, status='succeeded', currency='usd',
        amount_received=4900, amount=4900, latest_charge=CHARGE)
    charge = dict(id=CHARGE, livemode=True, payment_intent=PAYMENT, status='succeeded',
        paid=True, captured=True, refunded=False, disputed=False, amount_refunded=0,
        currency='usd', amount=4900, amount_captured=4900)
    if scenario == 'unpaid': session['payment_status'] = 'unpaid'
    elif scenario == 'underpaid': session['amount_total'] = 4800
    elif scenario == 'cancelled': session['status'] = 'expired'
    elif scenario == 'disputed': charge['disputed'] = True
    elif scenario == 'refunded': charge.update(refunded=True, amount_refunded=4900)
    elif scenario == 'invalid_session': session['id'] = SESSION+'invalid'
    return {'/v1/checkout/sessions/'+SESSION:session,
            '/v1/payment_intents/'+PAYMENT:payment, '/v1/charges/'+CHARGE:charge}


def serve_provider(scenario):
    """Owned, unauthenticated, loopback-only fake service; never Stripe testmode."""
    if scenario not in SCENARIOS: raise SimulationRejected('invalid_simulator_scenario')
    records = _records(scenario)
    class Handler(BaseHTTPRequestHandler):
        requests_seen = 0
        def log_message(self, *args): pass
        def do_GET(self):
            if (self.path not in records or self.headers.get('Content-Length', '0') != '0'
                    or Handler.requests_seen >= 128):
                self.send_error(404); return
            nonce = self.headers.get('X-BountyForge-Simulator-Nonce', '')
            if len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
                self.send_error(400); return
            Handler.requests_seen += 1
            raw = canonical({'kind':'phase8_provider_SIMULATOR', 'scenario':scenario,
                             'nonce':'0'*32 if scenario == 'replay' else nonce,
                             'record':records[self.path]})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers(); self.wfile.write(raw)
        def do_POST(self): self.send_error(405)
    server = HTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'provider_simulator':True, 'port':server.server_port}), flush=True)
    try: server.serve_forever(poll_interval=.1)
    finally: server.server_close()


class SimulatorStripeGate(StripeOrderGate):
    """Fixed loopback-only simulator; production PaidReviewLedger rejects its type."""
    def __init__(self, port):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise SimulationRejected('invalid_simulator_port')
        self.port, self.calls, self.scenario = port, 0, None
        # Deliberately no key, environment access or production constructor.
        self._link, self._amount = LINK, 4900

    def _get(self, group, identifier):
        allowed = {('checkout/sessions',SESSION), ('payment_intents',PAYMENT), ('charges',CHARGE)}
        if (group, identifier) not in allowed or self.calls >= 6:
            raise SimulationRejected('provider_evidence_rejected')
        self.calls += 1
        nonce = secrets.token_hex(16)
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            connection.request('GET', '/v1/'+group+'/'+identifier,
                               headers={'X-BountyForge-Simulator-Nonce':nonce,
                                        'User-Agent':'BountyForge-Owned-Simulator/1'})
            response = connection.getresponse()
            raw = response.read(8193)
            if response.status != 200 or len(raw) > 8192:
                raise SimulationRejected('provider_evidence_rejected')
            envelope = json.loads(raw)
            if (not isinstance(envelope, dict) or envelope.get('kind') != 'phase8_provider_SIMULATOR'
                    or envelope.get('nonce') != nonce or envelope.get('scenario') not in SCENARIOS
                    or not isinstance(envelope.get('record'), dict)):
                raise SimulationRejected('provider_evidence_rejected')
            if self.scenario is not None and envelope['scenario'] != self.scenario:
                raise SimulationRejected('provider_evidence_rejected')
            self.scenario = envelope['scenario']
            return envelope['record']
        except (OSError, http.client.HTTPException):
            raise SimulationRejected('provider_unavailable') from None
        except (ValueError, TypeError, KeyError):
            raise SimulationRejected('provider_evidence_rejected') from None
        finally:
            connection.close()

    def verify(self, session_id):
        if session_id != SESSION: raise SimulationRejected('invalid_session')
        try:
            proof = StripeOrderGate.verify(self, session_id)
        except OrderNotVerified:
            raise SimulationRejected('payment_not_verified') from None
        if proof.get('payment_verified') is not True:
            raise SimulationRejected('payment_not_verified')
        # Live-shaped fixture fields exercise existing validation, never escape
        # as a real-payment receipt or enter a production paid-review schema.
        return {'kind':'phase8_SIMULATED_payment_evidence', 'provider_simulator':True,
                'simulated_payment_verified':True, 'real_payment_verified':False,
                'session_sha256':digest(SESSION.encode()), 'execution_authorized':False,
                'owner_consent_verified':False}


def owned_verification_record():
    return {'kind':'phase8_independent_owned_replay', 'provider_simulator':True,
            'baseline_failed':True, 'repair_passed':True, 'vectors':4,
            'source_sha256':SOURCE_HASH, 'patch_sha256':PATCHED_HASH,
            'customer_code_executed':False, 'model_calls':0}


def independent_verify():
    check = replay(SOURCE, PATCHED)
    if not check['repair_passed']: raise SimulationRejected('owned_verification_failed')
    return owned_verification_record()


class SyntheticOrder:
    """One fixed owned order; existing owned ledger plus labeled simulation state."""
    def __init__(self, root, *, scope_ttl=300):
        if type(scope_ttl) is not int or not 1 <= scope_ttl <= 3600:
            raise SimulationRejected('invalid_scope_budget')
        self.root = require_private_directory(Path(root))
        if (_private_read(self.root / MARKER) != IDENTITY
                or any(p.name not in ALLOWED or p.is_symlink() for p in self.root.iterdir())):
            raise SimulationRejected('workspace_rejected')
        lock = self.root / 'phase8.SIMULATION_ONLY.lock'
        self.lock = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            _private_read(lock)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, SimulationRejected):
            os.close(self.lock); raise SimulationRejected('worker_busy') from None
        self.ledger = None
        try:
            path = self.root / DATABASE
            if path.exists():
                _private_read(path, 1024*1024)
                conn = sqlite3.connect(path)
                try:
                    identity = conn.execute('SELECT kind FROM simulation_only_identity').fetchall()
                    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if tables != {'jobs', 'events', 'simulation_only_identity',
                                  'simulation_only_order', 'simulation_only_evidence'}:
                        raise SimulationRejected('workspace_rejected')
                    if identity != [('phase8_PROVIDER_SIMULATOR_ONLY',)]:
                        raise SimulationRejected('workspace_rejected')
                finally: conn.close()
            self.ledger = OwnedOnlyLedger(path)
            db = self.ledger.db
            db.execute('CREATE TABLE IF NOT EXISTS simulation_only_identity '
                       '(id INTEGER PRIMARY KEY CHECK(id=1), kind TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO simulation_only_identity VALUES (1,'phase8_PROVIDER_SIMULATOR_ONLY')")
            db.execute('CREATE TABLE IF NOT EXISTS simulation_only_order '
                       '(id INTEGER PRIMARY KEY CHECK(id=1), rev INTEGER NOT NULL, '
                       'scope_expires INTEGER NOT NULL, held INTEGER NOT NULL, reason TEXT NOT NULL, '
                       'package_sha TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO simulation_only_order VALUES (1,0,?,0,?,?)',
                       (int(time.time())+scope_ttl, '', ''))
            db.execute('CREATE TABLE IF NOT EXISTS simulation_only_evidence '
                       '(kind TEXT PRIMARY KEY, record TEXT NOT NULL, record_sha256 TEXT NOT NULL)')
            self._validate_evidence()
            self._validate_owned_ledger()
        except BaseException:
            self.close(); raise

    def close(self):
        if self.ledger is not None:
            self.ledger.close()
            self.ledger = None
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None

    def state(self):
        row = self.ledger.db.execute('SELECT rev,scope_expires,held,reason,package_sha '
                                     'FROM simulation_only_order WHERE id=1').fetchone()
        if (row is None or type(row[0]) is not int or row[0] < 0 or type(row[1]) is not int
                or row[1] < 0 or row[2] not in (0,1)
                or row[3] not in ('', 'scope_expired', 'revoked', 'cancelled', 'payment_not_verified',
                                  'package_tampered', 'provider_evidence_rejected')
                or not isinstance(row[4], str) or (row[4] and
                    (len(row[4]) != 64 or any(c not in '0123456789abcdef' for c in row[4])))):
            raise SimulationRejected('workspace_rejected')
        return {'rev':row[0], 'expires':row[1], 'held':bool(row[2]), 'reason':row[3], 'package':row[4]}

    def _update(self, previous, *, held=None, reason=None, package=None):
        db = self.ledger.db
        db.execute('BEGIN IMMEDIATE')
        try:
            if self.state()['rev'] != previous['rev']: raise SimulationRejected('stale_revision')
            db.execute('UPDATE simulation_only_order SET rev=?,held=?,reason=?,package_sha=? WHERE id=1',
                       (previous['rev']+1, int(previous['held'] if held is None else held),
                        previous['reason'] if reason is None else reason,
                        previous['package'] if package is None else package))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK'); raise

    def hold(self, reason):
        if reason not in ('revoked', 'cancelled', 'scope_expired', 'payment_not_verified',
                          'package_tampered', 'provider_evidence_rejected'):
            raise SimulationRejected('invalid_hold')
        previous = self.state()
        if not previous['held']: self._update(previous, held=True, reason=reason)
        row = self.ledger.read(JOB)
        if row is not None and row['step'] != 'HELD':
            self.ledger.advance(JOB, row['rev'], 'HELD',
                                {'kind':'owned_hold', 'delivery_authorized':False})
        return result(status='held', state='HELD', reason=reason)

    def _check_scope(self):
        state = self.state()
        if state['held']: raise SimulationRejected('order_held')
        if int(time.time()) >= state['expires']:
            self.hold('scope_expired'); raise SimulationRejected('scope_expired')

    @staticmethod
    def _payment_record():
        return {'kind':'phase8_SIMULATED_payment_evidence', 'provider_simulator':True,
                'simulated_payment_verified':True, 'real_payment_verified':False,
                'session_sha256':digest(SESSION.encode()), 'execution_authorized':False,
                'owner_consent_verified':False}

    def _scope_record(self):
        return {'kind':'phase8_SYNTHETIC_scope', 'provider_simulator':True,
                'source_sha256':SOURCE_HASH, 'patch_sha256':PATCHED_HASH,
                'expires_at':self.state()['expires'], 'real_payment_verified':False,
                'owner_consent_verified':False, 'customer_rights_verified':False,
                'private_execution_authorized':False, 'delivery_authorized':False}

    def _record(self, kind, record):
        expected = {'simulated_payment':self._payment_record(),
                    'synthetic_scope':self._scope_record()}
        if kind not in expected or canonical(record) != canonical(expected[kind]):
            raise SimulationRejected('provider_evidence_rejected')
        raw = canonical(record)
        self.ledger.db.execute('INSERT OR IGNORE INTO simulation_only_evidence VALUES (?,?,?)',
                               (kind, raw.decode(), digest(raw)))
        self._validate_evidence()

    def _validate_evidence(self):
        expected = {'simulated_payment':self._payment_record(),
                    'synthetic_scope':self._scope_record()}
        for kind, raw, sha in self.ledger.db.execute(
                'SELECT kind,record,record_sha256 FROM simulation_only_evidence'):
            if kind not in expected or raw != canonical(expected[kind]).decode() or sha != digest(raw.encode()):
                raise SimulationRejected('ledger_tampered')

    def _validate_owned_ledger(self):
        """Validate the exact phase7 fixture history before resuming any job."""
        rows = self.ledger.db.execute('SELECT id,step,rev,evidence FROM jobs').fetchall()
        events = self.ledger.db.execute('SELECT id,rev,step,evidence_sha FROM events ORDER BY rev').fetchall()
        if not rows:
            if events: raise SimulationRejected('ledger_tampered')
            return
        history = [
            ('CREATED', {'kind':'owned_fixture','source_sha256':SOURCE_HASH,'real_payment_verified':False}),
            ('SCOPE_REVIEWED', {'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False}),
            ('PROPOSED', {'kind':'owned_patch','patch_sha256':PATCHED_HASH}),
            ('VERIFIED', replay(SOURCE,PATCHED)),
            ('AWAITING_OWNER_APPROVAL', {'kind':'owned_package',
                'package_sha256':digest(canonical(package_record(JOB))+b'\n'),'delivery_authorized':False})]
        if len(rows) != 1 or rows[0][0] != JOB or not events:
            raise SimulationRejected('ledger_tampered')
        held = events[-1][2] == 'HELD'
        count = len(events) - int(held)
        if not 1 <= count <= len(history): raise SimulationRejected('ledger_tampered')
        expected = [(JOB, rev, step, digest(canonical(evidence)))
                    for rev, (step,evidence) in enumerate(history[:count])]
        if held:
            history = history[:count] + [('HELD',{'kind':'owned_hold','delivery_authorized':False})]
            expected.append((JOB,count,'HELD',digest(canonical(history[-1][1]))))
        step, evidence = history[len(expected)-1]
        if events != expected or rows[0] != (JOB,step,len(expected)-1,canonical(evidence).decode()):
            raise SimulationRejected('ledger_tampered')
        kinds = {r[0] for r in self.ledger.db.execute('SELECT kind FROM simulation_only_evidence')}
        if kinds != {'simulated_payment','synthetic_scope'}:
            raise SimulationRejected('ledger_tampered')

    def _package(self):
        return {**result(status='review_package', state='AWAITING_OWNER_APPROVAL',
                         simulated_payment_verified=True, synthetic_scope_reviewed=True),
                'job_id':JOB, 'session_sha256':digest(SESSION.encode()),
                'simulated_payment_sha256':digest(canonical(self._payment_record())),
                'synthetic_scope_sha256':digest(canonical(self._scope_record())),
                'source_sha256':SOURCE_HASH, 'patch_sha256':PATCHED_HASH,
                'owned_package_sha256':digest(canonical(package_record(JOB))+b'\n'),
                'independent_verification_sha256':digest(canonical(owned_verification_record())+b'\n')}

    def _checkpoint(self, name, stop_after, pause):
        if pause and name == 'scope':
            print(json.dumps(result(status='checkpoint', state='SCOPE_REVIEWED', checkpoint='scope')), flush=True)
            select.select([], [], [], 10)
            raise SimulationRejected('interrupted')
        if stop_after == name: raise SimulationRejected('interrupted')

    def run(self, gate, *, stop_after=None, pause_after_scope=False):
        if type(gate) is not SimulatorStripeGate:
            raise SimulationRejected('simulator_required')
        started = False; independent = 0
        try:
            self._check_scope()
            proof = gate.verify(SESSION)
            self._record('simulated_payment', proof)
            self._checkpoint('payment', stop_after, False)
            self._check_scope()
            self._record('synthetic_scope', self._scope_record())
            self.ledger.create(JOB)  # Existing fixed owned job ID, idempotent.
            row = self.ledger.read(JOB)
            if row['step'] == 'CREATED':
                self.ledger.advance(JOB, row['rev'], 'SCOPE_REVIEWED',
                    {'kind':'owned_scope','real_payment_verified':False,'customer_rights_verified':False})
            self._checkpoint('scope', stop_after, pause_after_scope)
            row = self.ledger.read(JOB)
            duplicate = row['step'] == 'AWAITING_OWNER_APPROVAL'
            if duplicate:
                expected = canonical(self._package())+b'\n'
                if (_private_read(self.root / PACKAGE) != expected
                        or self.state()['package'] != digest(expected)
                        or _private_read(self.root / (JOB+'.review.json')) != canonical(package_record(JOB))+b'\n'
                        or _private_read(self.root / PROOF) != canonical(owned_verification_record())+b'\n'):
                    self.hold('package_tampered'); raise SimulationRejected('package_tampered')
            else:
                self._check_scope()
                started = True
                if row['step'] == 'SCOPE_REVIEWED':
                    self.ledger.advance(JOB,row['rev'],'PROPOSED',{'kind':'owned_patch','patch_sha256':PATCHED_HASH})
                self._checkpoint('proposed', stop_after, False)
                row = self.ledger.read(JOB)
                if row['step'] == 'PROPOSED':
                    self._check_scope()
                    command = [sys.executable,'-m','scripts.phase8_synthetic_order','verify-owned']
                    completed = subprocess.run(command, capture_output=True, timeout=5,
                        env={'PATH':os.defpath, 'PYTHONPATH':str(Path(__file__).resolve().parents[1]),
                             'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8'})
                    if (completed.returncode or len(completed.stdout)>8192 or completed.stderr
                            or json.loads(completed.stdout) != owned_verification_record()):
                        raise SimulationRejected('owned_verification_failed')
                    _write_exact(self.root / PROOF, canonical(owned_verification_record())+b'\n')
                    independent = 1
                    self.ledger.advance(JOB,row['rev'],'VERIFIED',replay(SOURCE,PATCHED))
                self._checkpoint('verified', stop_after, False)
                self._check_scope(); gate.verify(SESSION)  # Fresh status before final review.
                self._check_scope()
                if _private_read(self.root / PROOF) != canonical(owned_verification_record())+b'\n':
                    raise SimulationRejected('package_tampered')
                owned = canonical(package_record(JOB))+b'\n'
                _write_exact(self.root / (JOB+'.review.json'), owned)
                raw = canonical(self._package())+b'\n'; _write_exact(self.root / PACKAGE, raw)
                if self.state()['package'] != digest(raw):
                    self._update(self.state(), package=digest(raw))
                self._checkpoint('packaged', stop_after, False)
                self._check_scope()
                row = self.ledger.read(JOB)
                if row['step'] != 'VERIFIED': raise SimulationRejected('stale_revision')
                self.ledger.advance(JOB,row['rev'],'AWAITING_OWNER_APPROVAL',
                    {'kind':'owned_package','package_sha256':digest(owned),'delivery_authorized':False},
                    package_path=self.root / (JOB+'.review.json'))
            self._check_scope()
            output = result(status='already_reviewed' if duplicate else 'review_prepared',
                            state='AWAITING_OWNER_APPROVAL', simulated_payment_verified=True,
                            package_sha256=self.state()['package'],
                            owned_job_count=self.ledger.db.execute('SELECT count(*) FROM jobs').fetchone()[0])
            output.update(owned_fulfillment_started=started, provider_requests=gate.calls,
                          independent_owned_replays=independent)
            return 0, output
        except SimulationRejected as exc:
            reason = str(exc)
            if reason in ('payment_not_verified','provider_evidence_rejected','package_tampered'):
                self.hold(reason)
            output = result(status='interrupted' if reason=='interrupted' else 'rejected',
                            state='HELD' if self.state()['held'] else 'BLOCKED', reason=reason)
            output.update(owned_fulfillment_started=started, provider_requests=gate.calls,
                          independent_owned_replays=independent)
            return (3 if reason=='interrupted' else 2), output
