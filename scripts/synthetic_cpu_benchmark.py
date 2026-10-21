"""Bounded local-Qwen acceptance over three owned synthetic fixtures.

Never runs code downloaded from issue listings; never submits or claims rewards.
This is not the historical five-case Boltons benchmark or a production repair loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from bountyforge.autonomy import MODEL_SHA256, summarize_canary
from bountyforge.model import LocalModel
from bountyforge.worker import repair_fixture

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('addition', 'add(a, b) must return a+b'),
    ('multiply', 'multiply(a, b) must return a*b'),
    ('increment', 'increment(value) must return value increased by one'),
)


def run(model) -> dict:
    """Fixed catalog; downloaded issue text never becomes executable input."""
    results = []
    for name, description in CASES:
        fixture = ROOT / 'fixtures' / 'controlled' / name
        issue = {'title': 'Owned synthetic ' + name, 'verification': 'unverified_candidate',
                 'description_excerpt': description}
        raw = repair_fixture(issue, fixture, ['calc.py'], model,
                             strategy='auto_line', max_attempts=2)
        safe = summarize_canary(raw)
        results.append({'fixture': name, **safe})
    success = sum(r['status'] == 'synthetic_review_ready' for r in results)
    return {
        'kind': 'owned_synthetic_qwen_acceptance', 'version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'model_sha256_expected': MODEL_SHA256,
        'cases_attempted': len(CASES), 'cases_passed': success,
        'all_cases_passed': success == len(CASES),
        'results': results,
        'actual_revenue_usd': 0, 'real_bounty_repairs': 0,
        'external_submissions': 0, 'third_party_code_executed': False,
        'paid_inference': False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Synthetic-only real-Qwen acceptance')
    parser.add_argument('--local-port', type=int, choices=(8080, 18080), default=8080)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if os.environ.get('BOUNTYFORGE_SUBMIT_ENABLED', '0') != '0':
        raise ValueError('External submissions must remain disabled')
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError('Refuse invalid or existing output destination')
    model = LocalModel(endpoint=f'http://127.0.0.1:{args.local_port}/v1/chat/completions')
    # Do not pass GitHub credentials to the model or owned fixture subprocesses.
    os.environ.pop('GITHUB_TOKEN', None)
    record = run(model)
    raw = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    envelope = {'record': record, 'record_sha256': hashlib.sha256(raw).hexdigest()}
    fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os,'O_NOFOLLOW',0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(envelope, handle, indent=2, sort_keys=True)
        handle.write('\n')
    print(f"Owned synthetic fixtures: {record['cases_passed']}/{record['cases_attempted']} passed; "
          f"paid bounty repairs 0; external submissions 0")
    return 0 if record['all_cases_passed'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print('Synthetic acceptance failed closed: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(2)
