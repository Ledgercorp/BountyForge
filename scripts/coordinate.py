"""Trusted publication-plane coordinator. Never imports or executes candidate code."""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from bountyforge.autonomy import verify_envelope
from bountyforge.durable import DurableLedger, GitHubStore


def read_json(path, limit=65536):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:
        raise ValueError('Invalid coordination input')
    return json.loads(path.read_text())


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=('prepare','finish'))
    p.add_argument('--revision',required=True)
    p.add_argument('--discovery')
    p.add_argument('--claim',required=True)
    p.add_argument('--evidence')
    args=p.parse_args(argv)
    ledger=DurableLedger(GitHubStore())
    if args.action=='prepare':
        report=verify_envelope(read_json(args.discovery))
        if report['bountyforge_revision']!=args.revision: raise ValueError('Discovery revision mismatch')
        ledger.discover([x['issue_url'] for x in report['candidates']])
        ledger.enqueue_synthetic(args.revision,datetime.now(timezone.utc).date().isoformat())
        claim=ledger.claim()
        if claim and claim['input']['revision']!=args.revision:
            ledger.finish_failed(claim,'stale_source_revision')
            claim=ledger.claim()
        path=Path(args.claim)
        with path.open('x') as f: json.dump(claim,f)
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write('has_claim='+('true' if claim else 'false')+'\n')
        print('Durable claim acquired' if claim else 'No executable claim; duplicate or active lease')
        return 0
    claim=read_json(args.claim)
    if claim is None: return 0
    if claim['input']['revision']!=args.revision: raise ValueError('Claim revision mismatch')
    if args.evidence and Path(args.evidence).is_file():
        envelope=read_json(args.evidence)
        run_id=os.environ['GITHUB_RUN_ID']
        if not run_id.isdigit(): raise ValueError('Invalid run provenance')
        saved=ledger.finish_evidence(claim,envelope,'https://github.com/Ledgercorp/BountyForge/actions/runs/'+run_id)
    else:
        saved=ledger.finish_failed(claim,'workflow_failed_before_evidence')
    if not saved: raise RuntimeError('Expired or superseded lease; completion rejected')
    print('Verified internal result durably recorded; commercial submissions disabled')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
