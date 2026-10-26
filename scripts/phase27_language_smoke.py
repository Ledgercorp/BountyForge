"""Run hash-pinned, owned-only JavaScript and TypeScript smoke fixtures.

This runner has no configurable command, path, package installation, model
provider, or third-party repository input. Its results are developmental.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'evidence/phase27/language_fixture_manifest.json'
CASES=(
    {'profile':'JAVASCRIPT','flag':None,
     'baseline':'tests/phase27/javascript_baseline.test.mjs',
     'reference':'tests/phase27/javascript_reference.test.mjs'},
    {'profile':'TYPESCRIPT','flag':'--experimental-strip-types',
     'baseline':'tests/phase27/typescript_baseline.test.ts',
     'reference':'tests/phase27/typescript_reference.test.ts'},
)
EXPECTED_FILES=frozenset({
    'fixtures/phase27/javascript/retry_delay_buggy.mjs',
    'fixtures/phase27/javascript/retry_delay_reference.mjs',
    'fixtures/phase27/typescript/reservation_buggy.ts',
    'fixtures/phase27/typescript/reservation_reference.ts',
    'tests/phase27/javascript_baseline.test.mjs',
    'tests/phase27/javascript_reference.test.mjs',
    'tests/phase27/typescript_baseline.test.ts',
    'tests/phase27/typescript_reference.test.ts',
})


def _manifest():
    data=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if (type(data) is not dict or data.get('kind')!='BOUNTYFORGE_PHASE27_OWNED_LANGUAGE_FIXTURES'
            or data.get('classification')!='DEVELOPMENTAL_EXPOSED'
            or data.get('model_calls')!=0 or data.get('cases')!=[x['profile'] for x in CASES]
            or type(data.get('files')) is not dict or set(data['files'])!=EXPECTED_FILES):
        raise ValueError('PHASE27_FIXTURE_MANIFEST_REJECTED')
    for rel,digest in data['files'].items():
        pure=PurePosixPath(rel)
        if pure.is_absolute() or '..' in pure.parts or type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise ValueError('PHASE27_FIXTURE_MANIFEST_REJECTED')
        path=ROOT.joinpath(*pure.parts)
        info=path.lstat()
        if not path.is_file() or path.is_symlink() or info.st_nlink!=1:
            raise ValueError('PHASE27_FIXTURE_FILE_REJECTED')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('PHASE27_FIXTURE_DIGEST_MISMATCH')
    return data


def _run(node,case,mode,stage,workspace,env):
    test_path=case[mode]
    flags=([case['flag']] if case['flag'] else [])
    command=[node,*flags,'--test','--test-reporter=tap',test_path]
    started=time.monotonic()
    try:
        result=subprocess.run(command,cwd=workspace,env=env,text=True,capture_output=True,timeout=15,check=False)
    except subprocess.TimeoutExpired:
        return {'profile':case['profile'],'stage':stage,'status':'TIMEOUT','elapsed_seconds':round(time.monotonic()-started,3)}
    elapsed=round(time.monotonic()-started,3)
    output=(result.stdout+'\n'+result.stderr)[:65536]
    counts={}
    for key in ('tests','pass','fail','cancelled','skipped','todo'):
        match=re.search(r'^# '+key+r' (\d+)\s*$',output,re.M)
        counts[key]=int(match.group(1)) if match else None
    expected=2
    status='PASS' if result.returncode==0 and counts['tests']==expected and counts['pass']==expected and counts['fail']==0 else 'FAIL'
    return {'profile':case['profile'],'stage':stage,'status':status,'exit_code':result.returncode,
            'elapsed_seconds':elapsed,'test_counts':counts}


def run():
    manifest=_manifest()
    node=shutil.which('node')
    if not node:
        return {'kind':'BOUNTYFORGE_PHASE27_LANGUAGE_SMOKE','status':'BLOCKED_NODE_UNAVAILABLE',
                'model_calls':0,'third_party_execution_authorized':False}
    version=subprocess.run([node,'--version'],capture_output=True,text=True,timeout=5,check=False)
    node_version=version.stdout.strip()
    if version.returncode!=0 or not node_version.startswith('v24.'):
        return {'kind':'BOUNTYFORGE_PHASE27_LANGUAGE_SMOKE','status':'BLOCKED_NODE_VERSION',
                'node_version':node_version[:32],'model_calls':0,'third_party_execution_authorized':False}
    results=[]
    with tempfile.TemporaryDirectory(prefix='bf-phase27-owned-node-') as temp:
        root=Path(temp)/'work';root.mkdir(mode=0o700)
        for rel in EXPECTED_FILES:
            destination=root.joinpath(*PurePosixPath(rel).parts)
            destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            shutil.copyfile(ROOT.joinpath(*PurePosixPath(rel).parts),destination)
            destination.chmod(0o400)
        env={'PATH':str(Path(node).parent),'HOME':str(root),'TMPDIR':str(root),'CI':'1','NODE_NO_WARNINGS':'1'}
        for case in CASES:
            results.append(_run(node,case,'baseline','BASELINE_DEFECT_REPRODUCED',root,env))
            results.append(_run(node,case,'reference','PREAUTHORED_REFERENCE_PASSED',root,env))
    ok=all(x.get('status')=='PASS' for x in results)
    return {'kind':'BOUNTYFORGE_PHASE27_LANGUAGE_SMOKE','schema':1,
        'status':'PASSED' if ok else 'FAILED','classification':'DEVELOPMENTAL_EXPOSED',
        'manifest_sha256':hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        'node_version':node_version,'cases':results,'model_calls':0,'model_generated_repairs':0,
        'reference_repairs_model_generated':False,'network_access_enforced':False,
        'execution_scope':'EXACT_HASH_PINNED_LEFTSOCK_OWNED_FIXTURES',
        'third_party_execution_authorized':False,'dependency_installation':False,
        'deepseek_requests':0,'additional_spend_usd':'0'}


if __name__=='__main__':
    try:
        report=run()
    except (OSError,ValueError,subprocess.SubprocessError):
        report={'kind':'BOUNTYFORGE_PHASE27_LANGUAGE_SMOKE','status':'BLOCKED_OR_INVALID_FIXTURE',
                'model_calls':0,'third_party_execution_authorized':False}
    print(json.dumps(report,sort_keys=True))
    raise SystemExit(0 if report.get('status')=='PASSED' else 2)
