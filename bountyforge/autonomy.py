"""Fail-closed BountyForge discovery/evidence controller.

Only vetted, repository-owned synthetic fixtures may be executed. Public issues
are never converted to executable inputs, regardless of advertised rewards.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 1
MAX_REPORT_BYTES = 65536
MAX_CANDIDATES = 30
MODEL_SHA256 = 'cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046'
VALID_SCAN_SOURCES = frozenset({'fictional_demo', 'github_public_read_only'})
VALID_OUTCOMES = frozenset({'not_attempted', 'synthetic_review_ready', 'synthetic_failed'})


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _issue_url(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 300:
        return False
    p = urlsplit(value)
    return (p.scheme == 'https' and p.hostname == 'github.com'
            and p.username is None and p.password is None
            and p.port is None and p.query == '' and p.fragment == ''
            and bool(re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[1-9][0-9]*', p.path)))


def summarize_candidates(candidates: list[dict]) -> list[dict]:
    """Never allow issue content to choose an execution target or pollute logs."""
    if not isinstance(candidates, list):
        raise ValueError('Candidates must be a list')
    unique = {}
    for c in candidates[:MAX_CANDIDATES]:
        if not isinstance(c, dict) or not _issue_url(c.get('url')):
            continue
        url = c['url']
        if url in unique:
            continue
        unique[url] = {
            'issue_id': _digest(url.encode('utf-8')),
            'issue_url': url,
            'verification': 'unverified_candidate',
            'qualified_for_external_execution': False,
            'repair_attempted': False,
            'funding_verified': False,
            'blocker': 'Funding, participation terms and executable isolation not independently verified',
        }
    return sorted(unique.values(), key=lambda x: x['issue_id'])


def summarize_canary(result: dict) -> dict:
    """Return bounded metadata, excluding raw model, code, issue text, or test logs."""
    if not isinstance(result, dict):
        raise ValueError('Invalid controlled canary result')
    # Never replace contradictory worker facts with reassuring constant values.
    # A malformed, externally submitted, or non-synthetic record is inadmissible.
    if (result.get('controlled_synthetic_fixture') is not True
            or result.get('code_executed_in_trusted_fixture_only') is not True
            or result.get('submitted') is not False
            or result.get('verified_payout') is not False
            or result.get('paid_model_calls') != 0):
        raise ValueError('Unverified synthetic-only provenance or external activity')
    if result.get('status') not in {'review_ready', 'failed'}:
        raise ValueError('Unexpected worker terminal status')
    passed = result['status'] == 'review_ready'
    attempts = result.get('attempts', [])
    if not isinstance(attempts, list) or len(attempts) > 2:
        raise ValueError('Unbounded repair attempts')
    patch = result.get('patch')
    if patch is not None and not isinstance(patch, list):
        raise ValueError('Invalid patch evidence')
    patch_digest = None
    if patch:
        patch_digest = _digest(_canonical(patch))
    def test_meta(value):
        if not isinstance(value, dict):
            return None
        return {k: value.get(k) for k in ('passed', 'exit_code', 'timeout', 'seconds')}
    calls = result.get('model_calls', 0)
    if type(calls) is not int or not 0 <= calls <= 2 or calls != len(attempts):
        raise ValueError('Unbounded model calls')
    if passed and (not re.fullmatch(r'[0-9a-f]{64}', str(result.get('source_sha256') or ''))
                   or not isinstance(result.get('baseline'), dict)
                   or result['baseline'].get('passed') is not False
                   or not any(a.get('status') == 'passed'
                              and isinstance(a.get('test'), dict)
                              and a['test'].get('passed') is True for a in attempts)
                   or not patch):
        raise ValueError('Unsupported synthetic repair success claim')
    return {
        'status': 'synthetic_review_ready' if passed else 'synthetic_failed',
        'synthetic_only': True,
        'submitted': False,
        'third_party_code_executed': False,
        'model_calls': calls,
        'source_sha256': result.get('source_sha256'),
        'patch_sha256': patch_digest,
        'inferred_editable_lines': result.get('inferred_editable_lines', []),
        'baseline': test_meta(result.get('baseline')),
        'attempts': [{'number': a.get('number'), 'status': a.get('status'),
                      'test': test_meta(a.get('test'))} for a in attempts],
        'error': result.get('error'),
    }


def make_evidence(candidates: list[dict], *, scan_source: str, canary: dict | None = None,
                  revision: str | None = None, generated_at: str | None = None) -> dict:
    if scan_source not in VALID_SCAN_SOURCES:
        raise ValueError('Unrecognized discovery source')
    revision = revision or 'unavailable'
    if revision != 'unavailable' and not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Untrusted commit identifier')
    c = summarize_candidates(candidates)
    event = {
        'schema_version': VERSION,
        'generated_at': generated_at or datetime.now(timezone.utc).isoformat(),
        'bountyforge_revision': revision,
        'scan_source': scan_source,
        'scan_count': len(c),
        'candidates': c,
        'commercially_qualified': 0,
        'real_repairs_attempted': 0,
        'real_review_ready': 0,
        'external_submissions': 0,
        'revenue_usd_confirmed': 0,
        'paid_inference': False,
        'execution_scope': 'repository_owned_synthetic_fixture_only',
        'model_sha256_expected': MODEL_SHA256,
        'canary': canary if canary is not None else {'status': 'not_attempted'},
    }
    validate_evidence(event)
    return {'record': event, 'record_sha256': _digest(_canonical(event))}


def validate_evidence(document: dict) -> None:
    if not isinstance(document, dict) or set(document) != {'schema_version', 'generated_at',
            'bountyforge_revision', 'scan_source', 'scan_count', 'candidates',
            'commercially_qualified', 'real_repairs_attempted', 'real_review_ready',
            'external_submissions', 'revenue_usd_confirmed', 'paid_inference',
            'execution_scope', 'model_sha256_expected', 'canary'}:
        raise ValueError('Unexpected evidence schema')
    if document['schema_version'] != VERSION or document['scan_source'] not in VALID_SCAN_SOURCES:
        raise ValueError('Invalid evidence version or source')
    if not isinstance(document['candidates'], list) or len(document['candidates']) > MAX_CANDIDATES:
        raise ValueError('Invalid candidate count')
    if document['scan_count'] != len(document['candidates']):
        raise ValueError('Candidate count mismatch')
    for c in document['candidates']:
        if (not isinstance(c, dict) or set(c) != {'issue_id', 'issue_url', 'verification',
                'qualified_for_external_execution', 'repair_attempted', 'funding_verified', 'blocker'}
                or not _issue_url(c['issue_url']) or c['issue_id'] != _digest(c['issue_url'].encode())
                or c['verification'] != 'unverified_candidate'
                or c['qualified_for_external_execution'] is not False
                or c['repair_attempted'] is not False or c['funding_verified'] is not False):
            raise ValueError('Invalid or overpromoted candidate')
    for key in ('commercially_qualified', 'real_repairs_attempted', 'real_review_ready',
                'external_submissions', 'revenue_usd_confirmed'):
        if type(document[key]) is not int or document[key] != 0:
            raise ValueError('Unproven commercial or external claim')
    if (document['paid_inference'] is not False
            or document['execution_scope'] != 'repository_owned_synthetic_fixture_only'
            or document['model_sha256_expected'] != MODEL_SHA256):
        raise ValueError('Unsupported execution or inference claim')
    canary = document['canary']
    if not isinstance(canary, dict) or canary.get('status') not in VALID_OUTCOMES:
        raise ValueError('Invalid canary status')
    if canary['status'] == 'synthetic_review_ready' and (
            not isinstance(canary.get('baseline'), dict) or canary['baseline'].get('passed') is not False
            or not canary.get('patch_sha256')
            or not any(a.get('status') == 'passed' and isinstance(a.get('test'), dict)
                       and a['test'].get('passed') is True for a in canary.get('attempts', []))):
        raise ValueError('Unverified synthetic repair success')
    if canary['status'] != 'not_attempted' and (canary.get('synthetic_only') is not True
            or canary.get('submitted') is not False or canary.get('third_party_code_executed') is not False
            or type(canary.get('model_calls')) is not int or not 0 <= canary['model_calls'] <= 2):
        raise ValueError('Canary violated constraints')
    if not isinstance(document['generated_at'], str) or len(document['generated_at']) > 40:
        raise ValueError('Invalid timestamp')
    try:
        ts = datetime.fromisoformat(document['generated_at'].replace('Z', '+00:00'))
        if ts.tzinfo is None:
            raise ValueError('Timezone required')
    except (ValueError, TypeError) as exc:
        raise ValueError('Invalid timestamp') from exc
    if len(_canonical(document)) > MAX_REPORT_BYTES:
        raise ValueError('Oversized evidence')


def verify_envelope(envelope: dict) -> dict:
    if not isinstance(envelope, dict) or set(envelope) != {'record', 'record_sha256'}:
        raise ValueError('Invalid evidence envelope')
    validate_evidence(envelope['record'])
    if envelope['record_sha256'] != _digest(_canonical(envelope['record'])):
        raise ValueError('Evidence digest mismatch')
    return envelope['record']


def save_evidence(path: Path, envelope: dict) -> None:
    verify_envelope(envelope)
    path = Path(path)
    if path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError('Evidence destination must be an existing real directory')
    payload = json.dumps(envelope, indent=2, sort_keys=True) + '\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(payload)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
