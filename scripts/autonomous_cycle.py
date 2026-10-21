"""Read-only discoveries and optional trusted synthetic repair canary.

This does NOT execute third-party issue code or perform commercial submissions.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from bountyforge.autonomy import make_evidence, save_evidence, summarize_canary
from bountyforge.model import LocalModel
from bountyforge.scanner import normalize_issue, scan_github
from bountyforge.worker import repair_fixture

ROOT = Path(__file__).resolve().parents[1]

def main(argv=None):
    p = argparse.ArgumentParser(description='BountyForge bounded internal dry-run cycle')
    p.add_argument('--scan', choices=('offline', 'live'), default='offline')
    p.add_argument('--canary', action='store_true', help='Repair repository-owned synthetic fixture only')
    p.add_argument('--local-port', choices=(8080, 18080), default=8080, type=int)
    p.add_argument('--output', required=True)
    args = p.parse_args(argv)
    if os.getenv('BOUNTYFORGE_SUBMIT_ENABLED', '0') != '0':
        raise ValueError('External submission must remain disabled')
    if args.scan == 'offline':
        items = json.loads((ROOT / 'fixtures/demo_issues.json').read_text(encoding='utf-8'))
        candidates = [c for x in items if (c := normalize_issue(x)) is not None]
    else:
        candidates = scan_github(per_query=5)
    # Do not forward any scan credentials into the inference session.
    os.environ.pop('GITHUB_TOKEN', None)
    canary = None
    if args.canary:
        fixture = ROOT / 'fixtures/controlled/addition'
        issue = {'verification': 'unverified_candidate', 'title': 'Controlled addition test',
                 'description_excerpt': 'add(a, b) must return a+b'}
        model = LocalModel(endpoint=f'http://127.0.0.1:{args.local_port}/v1/chat/completions')
        canary = summarize_canary(repair_fixture(issue, fixture, ['calc.py'], model,
                                                 max_attempts=2, strategy='auto_line'))
    envelope = make_evidence(candidates, scan_source='fictional_demo' if args.scan == 'offline'
                             else 'github_public_read_only', canary=canary,
                             revision=os.getenv('GITHUB_SHA'))
    save_evidence(Path(args.output), envelope)
    print(f"Candidates {envelope['record']['scan_count']}; commercial approvals 0; "
          f"synthetic canary {envelope['record']['canary']['status']}; "
          f"digest {envelope['record_sha256']}; no external submissions")
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print('BountyForge cycle failed closed: ' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(2)
