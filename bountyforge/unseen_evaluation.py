"""Public-only handoff preparation. This module cannot grant evaluation blindness.

The external controller must keep tests/answers outside the agent's readable
filesystem and API permissions. No such verifier is admitted by this checkout.
"""
import ast
import re
from bountyforge.repair_engines import digest, encoded


PUBLIC_FIELDS={'task_id','source','source_sha256','requirements','verifier_commitment_sha256'}


def prepare_handoff(task):
    if type(task) is not dict or set(task)!=PUBLIC_FIELDS:
        raise ValueError('Only public task fields are allowed; no tests or solutions')
    if (type(task['task_id']) is not str or not re.fullmatch('[a-zA-Z0-9_-]{1,64}',task['task_id'])
            or type(task['source']) is not str or len(task['source'].encode())>12000
            or type(task['requirements']) is not str or not 1<=len(task['requirements'].encode())<=3000
            or any(type(task[key]) is not str or not re.fullmatch('[0-9a-f]{64}',task[key])
                   for key in ('source_sha256','verifier_commitment_sha256'))
            or digest(task['source'].encode())!=task['source_sha256']):
        raise ValueError('Invalid public evaluation handoff')
    ast.parse(task['source'])  # Parse only. Never imports or executes the source.
    return {'public_task':dict(task),'handoff_sha256':digest(encoded(task)),
            'held_out_blindness_verified':False,'independent_evaluation':False,
            'status':'EXTERNAL_CONTROLLER_NOT_ADMITTED','execution_authorized':False,
            'requirements_for_independent_evaluation':[
                'Tests and reference solutions controlled by a separate verifier identity',
                'No agent filesystem, tool or network route to held-out material',
                'Freeze public tasks and verifier commitments before generation',
                'Record generation transcript, candidate hash and signed external replay',
                'Audit the separation before classifying results as independent']}
