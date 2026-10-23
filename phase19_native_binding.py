"""Immutable native cache from the exact hash-pinned SDK carrier.

No host execution, downloads, Node patches, writable executable mounts or native
validation overrides. Only the release's own embedded Linux binding is staged.
"""
import hashlib
import json
import mmap
from pathlib import Path
import struct

RUNTIME_BIN='deepseek_harness_runtime/runtime/deepseek-harness-sdk-runtime-linux-x64'
CARRIER_SHA='b6f70327db1392b4ff879b8be26c87349b14933c1b4f7a90b391446bb005aae8'
BINDING_SHA='40c34d27d8339e246a8f7415a06152935496cdc06555ea8fce0e052011acc70f'
BINDING_MEMBER='/node/node_modules/node-addon-require-builtin-linux-x64-gnu/prebuilt/linux-x64-gnu-napi-v9.node'
CACHE_RELATIVE=Path('native-cache/node-addon-require-builtin-linux-x64-gnu/0.1.9/linux-x64-gnu/linux-x64-gnu-napi-v9.node')
MARKER=b'__pkg_manifest__'


def _regular(path):
    return not path.is_symlink() and path.is_file() and path.stat().st_nlink==1


def cache_admitted(root):
    root=Path(root);file=root/CACHE_RELATIVE
    try:
        if root.is_symlink() or not _regular(file) or file.stat().st_size!=295392:return False
        for p in (file,*file.parents):
            if p==root.parent:break
            if p.is_symlink() or p.stat().st_mode & 0o222:return False
        return hashlib.sha256(file.read_bytes()).hexdigest()==BINDING_SHA
    except OSError:return False


def stage_native_cache(root):
    root=Path(root);carrier=root/RUNTIME_BIN
    if root.is_symlink() or not _regular(carrier):raise RuntimeError('CARRIER_DIGEST_REJECTED')
    with carrier.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=CARRIER_SHA:raise RuntimeError('CARRIER_DIGEST_REJECTED')
        with mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:
            marker=data.rfind(MARKER)
            if marker<8 or data[marker-8:marker]!=struct.pack('<Q',len(MARKER)):
                raise RuntimeError('PINNED_CARRIER_MANIFEST_REJECTED')
            length=struct.unpack('<Q',data[marker+len(MARKER):marker+len(MARKER)+8])[0]
            start=marker+len(MARKER)+8
            if not 1<=length<=4*1024**2 or start+length>len(data):raise RuntimeError('PINNED_CARRIER_MANIFEST_REJECTED')
            manifest=json.loads(data[start:start+length]);offsets=manifest['offsets']
            if type(offsets) is not dict or not 1<=len(offsets)<=20000:raise RuntimeError('PINNED_CARRIER_MANIFEST_REJECTED')
            for pair in offsets.values():
                if (type(pair) is not list or len(pair)!=2 or any(type(x) is not int or x<0 for x in pair)
                        or sum(pair)>len(data)):raise RuntimeError('PINNED_CARRIER_MANIFEST_REJECTED')
            # Carrier stores the contiguous payload immediately before the
            # next length-prefixed manifest key. Offsets refer to that payload.
            base=marker-8-max(o+n for o,n in offsets.values())
            offset,size=offsets[BINDING_MEMBER]
            if base<0 or size!=295392 or base+offset+size>marker-8:raise RuntimeError('PINNED_BINDING_RANGE_REJECTED')
            binding=data[base+offset:base+offset+size]
    if (binding[:6]!=b'\x7fELF\x02\x01' or struct.unpack('<H',binding[18:20])[0]!=62
            or hashlib.sha256(binding).hexdigest()!=BINDING_SHA):raise RuntimeError('PINNED_BINDING_DIGEST_REJECTED')
    target=root/CACHE_RELATIVE
    if (root/'native-cache').exists():raise RuntimeError('NATIVE_CACHE_MUST_BE_NEW')
    target.parent.mkdir(parents=True)
    with target.open('xb') as out:out.write(binding)
    target.chmod(0o444)
    # Explicit permissions survive restrictive host umask; only public pinned
    # release data gets traversal. The container mount remains read-only.
    for p in root.rglob('*'):
        if p.is_symlink():raise RuntimeError('NATIVE_CACHE_SYMLINK_REJECTED')
        if p.is_dir():p.chmod(0o555)
    root.chmod(0o555)
    if not cache_admitted(root):raise RuntimeError('IMMUTABLE_NATIVE_CACHE_REJECTED')
    return {'carrier_sha256':CARRIER_SHA,'binding_sha256':BINDING_SHA,'binding_bytes':size,
            'native_package':'node-addon-require-builtin-linux-x64-gnu','native_package_version':'0.1.9',
            'backend':'napi','abi':'napi-v9','cache_mount_readonly':True,
            'writable_executable_storage_added':False,'runtime_binary_modified':False}
