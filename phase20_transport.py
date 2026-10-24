"""Private zero-egress SDK/model namespace, fixed public assets and limits."""
import hashlib
from pathlib import Path
import re
import shutil
import tarfile
from phase17_isolation import docker_command,IMAGE,PROBE,REQUIRED
from phase17_sdk_bootstrap import sdk_bootstrap_command
from bountyforge.model_profiles import profile_spec

MODEL_ID='bountyforge-qwen-1.5b'
PROVIDER_ID='bountyforge-local-qwen'
MODEL_NAME=re.compile(r'bf-p20-model-[0-9a-f]{16}\Z')
MODEL_PROBE=PROBE.replace('201326592','3221225472').replace('pids<=32','pids<=64').replace('quota<=period','quota<=2*period')
PROFILE_MODELS={'QWEN_1_5B':MODEL_ID,'GRANITE42_3B':'bountyforge-granite-3b'}


def file_hash(path):
    if path.is_symlink() or not path.is_file():raise ValueError('REGULAR_ASSET_REQUIRED')
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def stage_assets(destination,cache,*,profile='QWEN_1_5B'):
    if profile not in PROFILE_MODELS:raise ValueError('EXPLICIT_ADMITTED_MODEL_PROFILE_REQUIRED')
    spec=profile_spec(profile)
    archive=cache/'runtime/llama-b11750-bin-ubuntu-x64.tar.gz'
    if file_hash(archive)!=spec['runtime_sha256']:raise ValueError('RUNTIME_DIGEST_REJECTED')
    model=cache/'models'/spec['filename']
    if file_hash(model)!=spec['sha256']:raise ValueError('MODEL_DIGEST_REJECTED')
    if not destination.is_absolute() or destination.exists():raise ValueError('NEW_ASSET_STAGE_REQUIRED')
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            parts=Path(member.name).parts
            if (not parts or parts[0]!='llama-b11750' or len(parts)>2 or '..' in parts
                    or member.size>32*1024**2 or not (member.isdir() or member.isfile() or member.issym())):
                raise ValueError('PINNED_RUNTIME_LAYOUT_REJECTED')
            if member.issym() and (Path(member.linkname).is_absolute() or len(Path(member.linkname).parts)!=1):
                raise ValueError('PINNED_RUNTIME_SYMLINK_REJECTED')
        destination.mkdir(mode=0o755)
        bundle.extractall(destination,filter='data')
    shutil.copyfile(model,destination/'model.gguf')
    from phase20_dependency import stage_library,DEB_FILE
    dependency=stage_library(cache/'runtime'/DEB_FILE,destination/'deps')
    for path in destination.rglob('*'):
        if path.is_symlink():continue
        path.chmod(0o555 if path.is_dir() or path.name=='llama-server' else 0o444)
    destination.chmod(0o555)
    return {'model_sha256':spec['sha256'],'runtime_archive_sha256':spec['runtime_sha256'],
        'runtime_binary_sha256':file_hash(destination/'llama-b11750/llama-server'),
        'model_id':PROFILE_MODELS[profile],'license':'Apache-2.0','new_model_downloads':0,'dependency':dependency}


def model_command(docker,workspace,name,assets,*,profile='QWEN_1_5B'):
    if profile not in PROFILE_MODELS:raise ValueError('EXPLICIT_ADMITTED_MODEL_PROFILE_REQUIRED')
    if type(name) is not str or not MODEL_NAME.fullmatch(name):raise ValueError('OWNED_MODEL_NAMESPACE_REQUIRED')
    if not assets.is_absolute() or assets.is_symlink() or any(c in str(assets) for c in ',\n'):
        raise ValueError('MODEL_ASSET_PATH_REJECTED')
    base=docker_command(docker,workspace,'bf-p17-'+name[-16:])
    changes={'--name=bf-p17-'+name[-16:]:'--name='+name,'--memory=192m':'--memory=3g',
        '--memory-swap=192m':'--memory-swap=3g','--cpus=1':'--cpus=2','--pids-limit=32':'--pids-limit=64'}
    base=[changes.get(arg,arg) for arg in base]
    if profile=='GRANITE42_3B':
        base=[{'--memory=3g':'--memory=5g','--memory-swap=3g':'--memory-swap=5g'}.get(arg,arg) for arg in base]
    index=base.index(IMAGE)
    base[index:index]=['--mount=type=bind,source='+str(assets)+',target=/opt/qwen,readonly',
        '--env=LD_LIBRARY_PATH=/opt/qwen/deps:/opt/qwen/llama-b11750','--ulimit=cpu=180:180',
        '--ulimit=core=0:0','--ulimit=fsize=1048576:1048576','--ulimit=nofile=128:128']
    base[-6:]=[IMAGE,'python','-I','-B','/workspace/model_service.py']
    return base


def sdk_command(docker,workspace,name,native,model_name):
    if type(model_name) is not str or not MODEL_NAME.fullmatch(model_name):
        raise ValueError('OWNED_MODEL_NAMESPACE_REQUIRED')
    base=sdk_bootstrap_command(docker,workspace,name,native)
    return ['--network=container:'+model_name if x=='--network=none' else x for x in base]


def validate_model_boundary(record):
    if (type(record) is not dict or record.get('schema')!=1 or
            any(record.get(key) is not True for key in REQUIRED)):
        raise ValueError('MODEL_BOUNDARY_NOT_CONFIRMED')
    return record
