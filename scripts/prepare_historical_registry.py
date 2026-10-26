"""Bounded public metadata only. No repo/test/patch execution or inference."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request
from urllib.parse import urlencode
from collections import defaultdict
from bountyforge.evaluation_control import metadata_projection
from bountyforge.repair_engines import receipt_hash

DATASET='princeton-nlp/SWE-bench_Verified'
EXCLUDED={'astropy__astropy-12907':'Official web viewer exposed a reference preview during source research; excluded.'}


def get(url,limit):
    with urllib.request.urlopen(url,timeout=25) as r:raw=r.read(limit+1)
    if len(raw)>limit:raise ValueError('PUBLIC_METADATA_RESPONSE_LIMIT')
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def prepare():
    before,_=get('https://huggingface.co/api/datasets/'+DATASET+'?blobs=true',200000)
    groups=defaultdict(list);batches=[];rejected=[]
    for offset in range(0,500,50):
        url='https://datasets-server.huggingface.co/rows?'+urlencode({'dataset':DATASET,'config':'default','split':'test','offset':offset,'length':10})
        data,sha=get(url,4000000);batches.append({'offset':offset,'rows':len(data.get('rows',[])),'response_sha256':sha})
        for entry in data.get('rows',[]):
            row=entry.get('row',{});ident=row.get('instance_id','')
            if ident in EXCLUDED:rejected.append({'instance_id':ident,'reason':EXCLUDED[ident]});continue
            if entry.get('truncated_cells'):rejected.append({'instance_id':ident,'reason':'Truncated provider record'});continue
            try:fact=metadata_projection(row)
            except ValueError:rejected.append({'instance_id':ident,'reason':'Incomplete or bounded metadata contract rejected'});continue
            if len(fact['contamination_warnings'])>1:rejected.append({'instance_id':ident,'reason':'Issue may disclose solution'});continue
            fact['metadata_observation_sha256']=hashlib.sha256(json.dumps({k:row.get(k) for k in ('repo','instance_id','base_commit','FAIL_TO_PASS','PASS_TO_PASS')},sort_keys=True).encode()).hexdigest()
            groups[fact['repo']].append(fact)
        # Raw row payloads, patches/test patches/hints are discarded here, never
        # written, printed, passed to a model or exposed through agent_packet.
        del data
    selected=[];license_rejected=[]
    for round_no in range(5):
        for repo,items in sorted(groups.items()):
            if len(selected)>=30:break
            if round_no>=len(items):continue
            item=items[round_no]
            proc=subprocess.run(['gh','api','repos/'+repo+'/license?ref='+item['base_commit']],capture_output=True,text=True,timeout=25)
            if proc.returncode:
                license_rejected.append({'instance_id':item['instance_id'],'reason':'Exact revision source license not available'});continue
            license=json.loads(proc.stdout)
            spdx=license.get('license',{}).get('spdx_id')
            text=base64.b64decode(license.get('content','')).decode('utf-8','replace')
            normalized=' '.join(text.lower().split())
            notice=(('redistribution and use in source and binary forms' in normalized)
                    and 'modification, are permitted provided that' in normalized
                    and 'this software is provided' in normalized
                    and 'redistributions in binary form' in normalized)
            if spdx not in ('MIT','BSD-2-Clause','BSD-3-Clause','Apache-2.0') and not notice:
                license_rejected.append({'instance_id':item['instance_id'],'reason':'Source license unresolved or unsupported','reported_spdx':spdx});continue
            item['source_license']={'spdx':spdx,'primary_notice_review':'PERMISSIVE_BSD_NOTICE_PRESENT' if notice else 'GITHUB_RECOGNIZED_SPDX',
                                    'file_and_dependency_rights_admitted':False,'notice_sha256':hashlib.sha256(text.encode()).hexdigest(),'git_blob_sha':license['sha'],'path':license['path'],
                                    'source':'https://api.github.com/repos/'+repo+'/license?ref='+item['base_commit']}
            selected.append(item)
    after,_=get('https://huggingface.co/api/datasets/'+DATASET,200000)
    if before['sha']!=after['sha']:raise ValueError('DATASET_CHANGED_DURING_PREPARATION')
    assets=[{k:x.get(k) for k in ('rfilename','size','lfs')} for x in before.get('siblings',[]) if x['rfilename'].endswith('.parquet')]
    result={'kind':'PHASE23_HISTORICAL_METADATA_REGISTRY','dataset':DATASET,'observed_dataset_revision':before['sha'],
        'dataset_artifacts':assets,'dataset_card_license':before.get('cardData',{}).get('license'),
        'harness_license':'MIT','harness_repo':'SWE-bench/SWE-bench','harness_revision':'02e7a74ffd0b707aab73d203fe87bdc7c76afc8e',
        'dataset_license_scope':'Card has no explicit license; source licenses independently checked. Metadata facts only, no dataset issue text or code redistributed.',
        'viewer_revision_binding':'UNCONFIRMED: API exposes current rows; immutable local snapshot hashes and before/after dataset revision recorded',
        'tasks':selected,'rejected':rejected+license_rejected,'batches':batches,'checked_at_unix':int(time.time()),
        'repair_agent_saw_solutions':False,'reference_material_persisted':False,'actual_inference_requests':0,
        'upstream_code_executed':False,'functional_baselines_executed':0,'accuracy':None,
        'execution_admission':'BLOCKED_HOSTILE_CODE_SOURCE_TEST_RIGHTS_AND_BUDGET',
        'independently_unseen':False,'task_count':len(selected),'repos':sorted({t['repo'] for t in selected}),
        'acceptance_criteria':{'baseline':'All FAIL_TO_PASS fail and every PASS_TO_PASS passes without errors/skips',
                              'candidate':'Every required test passes, then fresh independent regression replay',
                              'partial_or_environment_failures':'Never counted as model accuracy'},
        'preparation_only':True,'paid_requests_authorized':0,'commercial_admission':'NOT_ADMITTED'}
    result['receipt_sha256']=receipt_hash(result);return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--admit-public-metadata',action='store_true',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv);r=prepare();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'task_count':r['task_count'],'repos':len(r['repos']),'actual_inference_requests':0,'upstream_code_executed':False}))
    return 0 if r['task_count']>=20 else 1


if __name__=='__main__':raise SystemExit(main())
