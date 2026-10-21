"""One bounded job per tick; controlled fixture only; no third-party code execution."""
from __future__ import annotations
from pathlib import Path
from bountyforge.queue import Queue
from bountyforge.worker import repair_fixture


def process_one(queue: Queue, fixture_catalog: dict[str, dict], model) -> dict:
    """Claim, run and durably record one queued synthetic repair.

    The queue payload contains only a fixture ID. The caller supplies a
    separately trusted fixture catalog; untrusted queue paths are ignored.
    """
    claim = queue.claim(lease_seconds=900)
    if claim is None:
        return {'state': 'idle', 'processed': 0}
    key = claim['input'].get('fixture_id')
    known = fixture_catalog.get(key)
    if not isinstance(known, dict):
        result = {'status':'failed', 'error':'unrecognized_fixture_id', 'submitted':False}
    else:
        try:
            result = repair_fixture(known['issue'], Path(known['root']), known['approved_paths'], model)
        except Exception as exc:
            result = {'status':'failed','error':type(exc).__name__, 'submitted':False}
    recorded=queue.finish(claim['id'],result,lease_token=claim['lease_token'])
    return {'state':result['status'], 'job_id':claim['id'], 'processed':1,
            'saved':recorded, 'result':result}
