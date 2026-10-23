"""Separate-process replay of hash-pinned owned candidates; no model generation."""
import tempfile
from pathlib import Path

from bountyforge.curated_tasks import editable_scope
from bountyforge.phase8_evaluation import validate_proof
from bountyforge.repair_engines import (ENGINES, OwnedVerifier, RepairRejected, catalog,
    digest, encoded, materialize, observation_summary, receipt_hash, strict_json)
from bountyforge.repair_session import validate_proposal_bindings
from bountyforge.statements import stage_statements


def replay_recording(raw, expected_sha256, *, verifier=None):
    if not isinstance(raw,bytes) or len(raw)>500000 or digest(raw)!=expected_sha256:
        raise RepairRejected('RECORDING_DIGEST_REJECTED')
    recording=strict_json(raw)
    specs={item['id']:item for item in catalog()}
    tasks={};candidates=[];seen=set()
    calls=recording.get('calls')
    if not isinstance(calls,list) or not 1<=len(calls)<=30:
        raise RepairRejected('BOUNDED_SESSION_RECORDING_REQUIRED')
    for call in calls:
        result=call.get('response',{}).get('result',{})
        if result.get('isError') is not False:continue
        content=result.get('content',[])
        if len(content)!=1 or content[0].get('type')!='text':
            raise RepairRejected('AMBIGUOUS_SESSION_RESPONSE')
        value=strict_json(content[0]['text'])
        if call.get('tool')=='prepare_owned_repair' and value.get('task_id'):
            if value['task_id'] in tasks:raise RepairRejected('DUPLICATE_TASK_IDENTITY')
            tasks[value['task_id']]=value
        if value.get('outcome')!='VERIFIED':continue
        task=tasks.get(value.get('task_id'));spec=specs.get(value.get('case_id'))
        if (task is None or spec is None or value['task_id'] in seen
                or value.get('engine') not in ENGINES or value.get('engine')!=task.get('engine')
                or value.get('receipt_sha256')!=receipt_hash(value)
                or value.get('source_sha256')!=spec['sha256']['subject.py']
                or value.get('tests_sha256')!=spec['sha256']['tests/test_regression.py']
                or digest(task.get('source','').encode())!=value.get('source_sha256')
                or value.get('independently_verified') is not True
                or value.get('independent_evaluation') is not False
                or value.get('delivery_authorized') is not False
                or value.get('customer_execution_authorized') is not False):
            raise RepairRejected('RECORDED_CANDIDATE_BINDING_REJECTED')
        scope=task.get('editable_lines')
        if (not isinstance(scope,list) or not scope
                or not set(scope)<=set(editable_scope(task['source'],spec['symbol']))):
            raise RepairRejected('RECORDED_SCOPE_REJECTED')
        proposal=value.get('proposal')
        proposal_raw=proposal.encode() if type(proposal) is str else encoded(proposal)
        if digest(proposal_raw)!=value.get('proposal_sha256'):
            raise RepairRejected('RECORDED_PROPOSAL_REJECTED')
        with tempfile.TemporaryDirectory(prefix='bf-phase12-replay-stage-') as directory:
            root=Path(directory)/'task';materialize(spec,root)
            candidate=stage_statements(proposal_raw.decode(),root,'subject.py',scope,value['source_sha256'])['files'][0]
            validate_proposal_bindings(task['source'],scope,proposal_raw.decode())
        if (candidate['content']!=value.get('candidate') or candidate['diff']!=value.get('diff')
                or digest(candidate['content'].encode())!=value.get('candidate_sha256')):
            raise RepairRejected('RECORDED_PATCH_REJECTED')
        seen.add(value['task_id']);candidates.append((spec,candidate,value))
    if not 1<=len(candidates)<=4:
        raise RepairRejected('NO_BOUNDED_VERIFIED_CANDIDATES')
    verifier=verifier if verifier is not None else OwnedVerifier()
    proof=verifier.preflight();validate_proof(proof)
    report={'kind':'phase12_recorded_candidate_independent_replay','model_generation_calls':0,
            'recording_sha256':expected_sha256,'runtime_admission':proof,'cases':[],
            'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
            'authorship_identity_attested':False,'delivery_authorized':False,
            'private_execution_admitted':False}
    for spec,candidate,record in candidates:
        observation=verifier.observe(spec,candidate['content'])
        report['cases'].append({'case_id':spec['id'],'engine':record['engine'],
            'candidate_sha256':record['candidate_sha256'],'original_receipt_sha256':record['receipt_sha256'],
            'verification':observation_summary(observation)})
    report['replay_passed']=all(item['verification']['passed'] for item in report['cases'])
    report['receipt_sha256']=receipt_hash(report)
    return report
