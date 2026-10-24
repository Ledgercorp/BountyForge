"""Actual pinned-native grammar QA with vocabulary only, never AI inference."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from phase17_isolation import docker_command,PROBE,IMAGE,validate_observation
from phase19_sdk_acceptance import remove_container
from phase20_native_agent import ENV,public_file
from phase20_transport import file_hash
from phase20_dependency import LIB_SHA
from phase21_reasoning import output_grammar
from phase21_wire_contract import linked_diagnosis_grammar
from bountyforge.model_profiles import profile_spec
from bountyforge.repair_engines import receipt_hash

ROOT=Path(__file__).resolve().parent


def admitted_assets(assets,archive):
    spec=profile_spec()
    if (not assets.is_absolute() or assets.is_symlink() or ',' in str(assets)
            or file_hash(archive)!=spec['runtime_sha256'] or file_hash(assets/'model.gguf')!=spec['sha256']
            or file_hash(assets/'deps/libgomp.so.1')!=LIB_SHA):raise ValueError('PINNED_VOCABULARY_ASSETS_REQUIRED')
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            path=assets/member.name
            if member.isfile():
                with bundle.extractfile(member) as stream:expected=hashlib.file_digest(stream,'sha256').hexdigest()
                if file_hash(path)!=expected:raise ValueError('PINNED_NATIVE_LIBRARY_REQUIRED')
            elif member.issym():
                if not path.is_symlink() or path.readlink()!=Path(member.linkname):raise ValueError('PINNED_NATIVE_LINK_REQUIRED')
    return {'model_sha256':spec['sha256'],'runtime_archive_sha256':spec['runtime_sha256'],'abi_header_sha256':'961430f89e2553dbcd99e3e6c59826af9ec143f05911520c74f804d986ff3cd2'}


def run(enabled=False,*,assets=None,archive=None):
    if enabled is not True:raise ValueError('EXPLICIT_VOCABULARY_ONLY_QA_REQUIRED')
    from bountyforge.phase8_evaluation import require_credential_free_host
    require_credential_free_host();proof=admitted_assets(assets,archive)
    task={'source':'def normalize(value):\n    selected = value\n    return selected\n','editable_lines':[2,3],
        'edit_units':[{'line':2,'end_line':2,'kind':'statement'},{'line':3,'end_line':3,'kind':'statement'}]}
    diag={'anchor':2,'cause':'state','expected':'Preserve returned value','risk':'none'}
    raw_cases=[('canonical_valid',diag,2,'selected = value + 1',True),
        ('anchor_not_in_changes',diag,3,'return value + 1',False),
        ('source_carriage_return',diag,2,'selected = value\r',False),
        ('diagnostic_tab',{**diag,'expected':'Preserve\tvalue'},2,'selected = value',False),
        ('literal_backslash_escape',diag,2,'selected = "\\t"',True),
        ('bounded_multiline_statement',diag,2,'selected = value\nselected += 1',True)]
    cases=[{'name':name,'text':json.dumps({'diagnosis':d,'changes':[{'line':line,'new':new}]},separators=(',',':')),
        'strict_expected':expected} for name,d,line,new,expected in raw_cases]
    grammars={'baseline':output_grammar(task,True),'linked_printable':linked_diagnosis_grammar(task)}
    docker=shutil.which('docker')
    if not docker:raise ValueError('DOCKER_REQUIRED')
    name='bf-p17-'+uuid.uuid4().hex[:16]
    with tempfile.TemporaryDirectory(prefix='bf21-wire-qa-') as temp:
        work=Path(temp);work.chmod(0o755)
        public_file(work/'owned.txt','owned-development-only\n')
        public_file(work/'probe.py',(ROOT/'tests/phase21_vocab_probe.py').read_bytes())
        public_file(work/'boundary.py',PROBE)
        public_file(work/'cases.json',json.dumps({'grammars':grammars,'witnesses':cases}))
        command=docker_command(docker,work,name);i=command.index(IMAGE)
        command[i:i]=['--mount=type=bind,source='+str(assets)+',target=/opt/qwen,readonly',
            '--env=LD_LIBRARY_PATH=/opt/qwen/deps:/opt/qwen/llama-b11750','--ulimit=cpu=30:30',
            '--ulimit=core=0:0','--ulimit=fsize=1048576:1048576']
        command=command[:command.index(IMAGE)]+[IMAGE,'python','-I','-B','/workspace/probe.py']
        try:
            result=subprocess.run(command,capture_output=True,timeout=35,env=ENV)
            if result.returncode or len(result.stdout)>32768:raise ValueError('CONTAINED_VOCABULARY_QA_FAILED')
            record=json.loads(result.stdout)
            if b'vocab only - skipping tensors' not in result.stderr:raise ValueError('VOCAB_ONLY_NOT_CONFIRMED')
            validate_observation(json.dumps(record['boundary_before']));validate_observation(json.dumps(record['boundary_after']))
        finally:remove_container(docker,name)
    observed={(r['grammar'],r['witness']):r['accepted'] for r in record['rows']}
    for case in cases:
        if observed[('baseline',case['name'])] is not True or observed[('linked_printable',case['name'])]!=case['strict_expected']:
            raise ValueError('NATIVE_GRAMMAR_CONFORMANCE_FAILED')
    record.update(status='PASSED',classification='NEUTRAL_FORMAT_CONTRACT_ONLY',assets=proof,
        no_model_weights_log_confirmed=True,containers_absent_after_cleanup=True,
        grammar_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in grammars.items()},
        new_repairs=0,additional_spending_usd=0,commercial_admission='NOT_ADMITTED',
        limitation='No neural forward pass or patch verification; live repair accuracy of this stricter optional grammar is unmeasured.')
    record['receipt_sha256']=receipt_hash(record)
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--admit-vocabulary-only-qa',action='store_true')
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
    if not args.admit_vocabulary_only_qa:p.error('Explicit no-inference vocabulary QA admission required')
    r=run(True,assets=args.assets,archive=args.archive);args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':r['status'],'model_requests':0,'model_forward_passes':0,'new_repairs':0}));return 0


if __name__=='__main__':raise SystemExit(main())
