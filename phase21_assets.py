"""Acquire three fixed public artifacts as inert bytes; never install/execute."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
from bountyforge.model_profiles import profile_spec,RUNTIME_SHA256
from phase20_dependency import DEB_FILE,DEB_SHA,DEB_URL


def acquire():
    from bountyforge.phase8_evaluation import require_credential_free_host
    require_credential_free_host()
    spec=profile_spec('GRANITE42_3B');cache=Path.home()/'.cache/bountyforge'
    sources=[(cache/'models'/spec['filename'],
        f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{spec['filename']}",spec['sha256'],spec['bytes']),
        (cache/'runtime/llama-b11750-bin-ubuntu-x64.tar.gz',
         'https://github.com/ggml-org/llama.cpp/releases/download/b11750/llama-b11750-bin-ubuntu-x64.tar.gz',RUNTIME_SHA256,22240456),
        (cache/'runtime'/DEB_FILE,DEB_URL,DEB_SHA,115772)]
    rows=[]
    for target,url,digest,size in sources:
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():raise ValueError('REGULAR_PUBLIC_ASSET_REQUIRED')
        if target.exists():
            if target.stat().st_size!=size or hashlib.file_digest(target.open('rb'),'sha256').hexdigest()!=digest:
                raise ValueError('CACHED_ASSET_DIGEST_REJECTED')
            rows.append({'file':target.name,'sha256':digest,'bytes':size,'downloaded':False});continue
        temporary=target.with_suffix(target.suffix+'.phase21-part');started=time.monotonic();total=0;hasher=hashlib.sha256()
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'wb') as out,urllib.request.urlopen(url,timeout=60) as response:
                while True:
                    if time.monotonic()-started>300:raise ValueError('PUBLIC_ASSET_WALL_LIMIT')
                    block=response.read(1024*1024)
                    if not block:break
                    total+=len(block)
                    if total>size:raise ValueError('PUBLIC_ASSET_SIZE_LIMIT')
                    hasher.update(block);out.write(block)
            if total!=size or hasher.hexdigest()!=digest:raise ValueError('PUBLIC_ASSET_DIGEST_REJECTED')
            temporary.replace(target)
        finally:
            if temporary.exists():temporary.unlink()
        rows.append({'file':target.name,'sha256':digest,'bytes':size,'downloaded':True})
    return {'kind':'PHASE21_INERT_PUBLIC_ASSET_ACQUISITION','files':rows,'installer_executed':False,'model_requests':0,'additional_spending_usd':0}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--admit-inert-public-assets',action='store_true')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
    if not args.admit_inert_public_assets:p.error('Explicit verified public asset acquisition required')
    result=acquire();args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print('Fixed public asset hashes verified; no installer or inference');return 0


if __name__=='__main__':raise SystemExit(main())
