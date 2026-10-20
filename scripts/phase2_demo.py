"""Explicit one-task real-Qwen synthetic worker acceptance; no third-party actions."""
from __future__ import annotations
import argparse
import json
import pathlib
import uuid
from bountyforge.model import LocalModel
from bountyforge.operator import process_one
from bountyforge.queue import Queue

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-port', type=int, choices=(8080,18080), default=18080)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--queue', type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    issue = {
        'url':'https://github.com/leftsock-labs/synthetic/issues/1',
        'title':'Synthetic regression: add returns subtraction',
        'description_excerpt':'Change the add(a,b) function to return a+b. Preserve tests.',
        'verification':'unverified_candidate',
    }
    model = LocalModel(endpoint=f'http://127.0.0.1:{args.local_port}/v1/chat/completions')
    queue = Queue(args.queue)
    try:
        ident = 'synthetic-' + uuid.uuid4().hex[:12]
        queue.enqueue(ident, {'fixture_id':'addition'})
        result = process_one(queue, {
            'addition': {
                'root':ROOT/'fixtures'/'controlled'/'addition',
                'approved_paths':['calc.py'],
                'issue':issue
            },
        },model)
        with args.output.open('x',encoding='utf-8') as fh:
            json.dump(result, fh, indent=2)
        print('Synthetic acceptance:',result['state'])
        return 0 if result['state']=='review_ready' else 1
    finally:
        queue.close()

if __name__ == '__main__':
    raise SystemExit(main())
