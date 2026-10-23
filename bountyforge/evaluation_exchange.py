"""Controller/agent interchange without assuming a controller is independent.

These deterministic envelopes convey public tasks and candidate commitments.
They grant no execution permission, and a caller cannot upgrade blindness.
"""
from bountyforge.unseen_evaluation import prepare_handoff
from bountyforge.repair_engines import ENGINES, encoded, digest, strict_json


def freeze_public_tasks(tasks):
    if type(tasks) is not list or not 1<=len(tasks)<=20:raise ValueError('Bounded public suite required')
    handoffs=[prepare_handoff(task) for task in tasks]
    if len({h['public_task']['task_id'] for h in handoffs})!=len(handoffs):raise ValueError('Duplicate public task')
    body={'schema':1,'handoffs':handoffs,'independent_evaluation':False,
          'controller_admitted':False,'execution_authorized':False}
    return {**body,'suite_sha256':digest(encoded(body))}


def bind_candidate(handoff,engine,proposal):
    if type(handoff) is not dict or engine not in ENGINES:raise ValueError('Explicit public handoff and engine required')
    checked=prepare_handoff(handoff.get('public_task'))
    if checked!=handoff:raise ValueError('Public handoff or admission flags changed')
    raw=encoded(proposal)
    if len(raw)>3000:raise ValueError('Candidate exceeds exchange budget')
    value=strict_json(raw)
    if type(value) is not dict or set(value)!={'changes'} or type(value['changes']) is not list or not 1<=len(value['changes'])<=3:
        raise ValueError('Bounded proposal required')
    for change in value['changes']:
        if (type(change) is not dict or set(change)!={'line','new'} or type(change['line']) is not int
                or not 1<=change['line']<=200 or type(change['new']) is not str or len(change['new'].encode())>400):
            raise ValueError('Proposal shape rejected')
    body={'schema':1,'task_id':checked['public_task']['task_id'],'engine':engine,
          'handoff_sha256':checked['handoff_sha256'],'proposal_sha256':digest(raw),'proposal':proposal,
          'source_sha256':checked['public_task']['source_sha256'],
          'verifier_commitment_sha256':checked['public_task']['verifier_commitment_sha256'],
          'independent_evaluation':False,'execution_authorized':False}
    return {**body,'submission_sha256':digest(encoded(body))}
