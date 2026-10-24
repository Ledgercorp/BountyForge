"""Inert extraction of one Debian-signed-index-pinned GCC runtime library.

No installer, lifecycle script, package manager, network or host execution.
Provenance chain and repository signature results are recorded in Phase20 evidence.
"""
import hashlib
import io
import tarfile

DEB_FILE='libgomp1_12.2.0-14+deb12u1_amd64.deb'
DEB_URL='https://deb.debian.org/debian/pool/main/g/gcc-12/'+DEB_FILE
DEB_SHA='48fec46bda7f5b1638b9e959889bfbc20491247d402d120bb152687eb48143d7'
LIB_SHA='f9a9ad78a8dc39c0e90a265ffa551fae6c92a40f360889b44a7e141f9a2adfb1'


def stage_library(package,destination):
    if package.is_symlink() or not package.is_file() or package.stat().st_size!=115772:
        raise ValueError('LIBGOMP_PACKAGE_DIGEST_REJECTED')
    data=package.read_bytes()
    if hashlib.sha256(data).hexdigest()!=DEB_SHA:raise ValueError('LIBGOMP_PACKAGE_DIGEST_REJECTED')
    cursor=8;payload=None
    if not data.startswith(b'!<arch>\n'):raise ValueError('LIBGOMP_ARCHIVE_REJECTED')
    while cursor<len(data):
        header=data[cursor:cursor+60];size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
        if name=='data.tar.xz':payload=data[cursor+60:cursor+60+size]
        cursor+=60+size+(size%2)
    if payload is None:raise ValueError('LIBGOMP_PAYLOAD_MISSING')
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:xz') as bundle:
        member=bundle.getmember('./usr/lib/x86_64-linux-gnu/libgomp.so.1.0.0')
        if not member.isfile() or member.size!=290392:raise ValueError('LIBGOMP_MEMBER_REJECTED')
        library=bundle.extractfile(member).read()
    if hashlib.sha256(library).hexdigest()!=LIB_SHA:raise ValueError('LIBGOMP_LIBRARY_DIGEST_REJECTED')
    destination.mkdir(mode=0o700)
    try:
        file=destination/'libgomp.so.1';file.write_bytes(library);file.chmod(0o444)
    finally:destination.chmod(0o555)
    return {'package':DEB_FILE,'package_sha256':DEB_SHA,'library_sha256':LIB_SHA,
        'license':'GPL-3.0-or-later WITH GCC-exception-3.1','installer_executed':False}
