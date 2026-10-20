"""Explicit local AI draft command; never checks out, executes, commits or submits."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from bountyforge.coder import propose_draft
from bountyforge.drafts import DraftRejected
from bountyforge.model import LocalModel


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='BountyForge local-only draft proposal')
    p.add_argument('--report',required=True,help='Local scan report JSON')
    p.add_argument('--issue',required=True,help='Exact GitHub issue URL in report')
    p.add_argument('--workspace',required=True,help='Read-only checkout of an approved target repo')
    p.add_argument('--file',required=True,action='append',dest='files',help='Approved existing file (repeat up to three)')
    p.add_argument('--output',required=True,help='Review manifest output outside the target checkout')
    p.add_argument('--local-port', type=int, choices=(8080,18080), default=8080,
                   help='Approved local llama.cpp port')
    args=p.parse_args(argv)
    source=Path(args.report).resolve(strict=True)
    report=json.loads(source.read_text(encoding='utf-8'))
    candidates=report.get('candidates', []) if isinstance(report,dict) else []
    matched=[x for x in candidates if isinstance(x,dict) and x.get('url')==args.issue]
    if len(matched)!=1:
        raise DraftRejected('Issue URL not uniquely present in local scan report')
    root=Path(args.workspace).resolve(strict=True)
    destination=Path(args.output).resolve()
    if destination.is_relative_to(root) or destination==source or destination.is_symlink():
        raise DraftRejected('Refusing to write review manifest inside target checkout or over source')
    local=LocalModel(endpoint=f'http://127.0.0.1:{args.local_port}/v1/chat/completions')
    result=propose_draft(matched[0],root,args.files,model=local)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Avoid overwriting a pre-existing report, even when it is not a symlink.
    with destination.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,ensure_ascii=False)
        handle.write('\n')
    print('Created review-only draft:',destination,'| files:',len(result['files']))
    print('No code was executed or changed in the target checkout; no external submissions.')
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (DraftRejected,OSError,ValueError,RuntimeError,json.JSONDecodeError) as exc:
        print('BountyForge draft refused:',exc,file=sys.stderr)
        raise SystemExit(2)
