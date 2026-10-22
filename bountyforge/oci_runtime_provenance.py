"""Offline OCI image descriptor closure for *review*, never execution admission.

The caller must supply bytes independently obtained from the registry. A digest
bound to mutable or attacker-supplied data does not authenticate the publisher.
No registry requests, archive unpacking, layer execution or customer source.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re

INDEX = 'application/vnd.oci.image.index.v1+json'
DOCKER_INDEX = 'application/vnd.docker.distribution.manifest.list.v2+json'
MANIFEST = 'application/vnd.oci.image.manifest.v1+json'
DOCKER_MANIFEST = 'application/vnd.docker.distribution.manifest.v2+json'
CONFIG = 'application/vnd.oci.image.config.v1+json'
DOCKER_CONFIG = 'application/vnd.docker.container.image.v1+json'
LAYERS = frozenset({
    'application/vnd.oci.image.layer.v1.tar+gzip',
    'application/vnd.oci.image.layer.v1.tar+zstd',
    'application/vnd.docker.image.rootfs.diff.tar.gzip',
})
SHA = re.compile(r'sha256:[0-9a-f]{64}\Z')
MAX_METADATA = 2 * 1024 * 1024
MAX_LAYERS = 100
MAX_LAYER_BYTES = 2 * 1024 * 1024 * 1024


class OCIReviewRejected(ValueError):
    """No reliable, complete OCI metadata chain could be established."""


def _digest(value):
    if type(value) is not str or not SHA.fullmatch(value):
        raise OCIReviewRejected('Invalid sha256 descriptor')
    return value


def _strict_json(raw):
    def no_duplicates(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                raise ValueError('Duplicate JSON key')
            seen[key] = value
        return seen
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def _read(raw, *, digest=None, allowed):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_METADATA:
        raise OCIReviewRejected('Missing or excessive OCI metadata')
    actual = 'sha256:' + hashlib.sha256(raw).hexdigest()
    if digest is not None and not hmac.compare_digest(actual, _digest(digest)):
        raise OCIReviewRejected('OCI blob differs from advertised digest')
    try:
        obj = _strict_json(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise OCIReviewRejected('Malformed OCI JSON') from None
    if (type(obj) is not dict or type(obj.get('schemaVersion')) is not int
            or obj['schemaVersion'] != 2 or obj.get('mediaType') not in allowed):
        raise OCIReviewRejected('Unknown OCI metadata type or schema')
    return obj, actual


def _descriptor(data, allowed):
    if (type(data) is not dict or type(data.get('mediaType')) is not str
            or data['mediaType'] not in allowed):
        raise OCIReviewRejected('Untrusted OCI descriptor type')
    digest = _digest(data.get('digest'))
    size = data.get('size')
    if type(size) is not int or not 0 < size <= MAX_LAYER_BYTES:
        raise OCIReviewRejected('Unbounded OCI descriptor')
    if 'urls' in data or 'data' in data:
        raise OCIReviewRejected('External or embedded blob references prohibited')
    return digest, size


def verify_oci_manifest_chain(index_bytes, manifest_bytes, config_bytes,
                              *, expected_index_digest):
    """Verify index -> one linux/amd64 manifest -> config metadata by SHA.

    Layer bytes, builder origin, signature, live registry identity and SBOM are
    NOT verified. The SHA-256 index pin must come from a separate trusted policy.
    """
    pinned = _digest(expected_index_digest)
    index, actual = _read(index_bytes, digest=pinned, allowed=(INDEX, DOCKER_INDEX))
    descriptors = index.get('manifests')
    if type(descriptors) is not list or not 1 <= len(descriptors) <= 64:
        raise OCIReviewRejected('Missing or excessive platform manifests')
    matches = []
    for item in descriptors:
        digest, size = _descriptor(item, (MANIFEST, DOCKER_MANIFEST,
                                          'application/vnd.oci.image.manifest.v1+json'))
        platform = item.get('platform')
        if type(platform) is not dict:
            raise OCIReviewRejected('Platform metadata missing')
        if platform.get('os') == 'linux' and platform.get('architecture') == 'amd64':
            if platform.get('variant') not in (None, ''):
                raise OCIReviewRejected('Ambiguous platform variant')
            matches.append((digest, size))
    if len(matches) != 1:
        raise OCIReviewRejected('Exactly one linux/amd64 manifest required')
    child_digest, child_size = matches[0]
    if type(manifest_bytes) is not bytes or child_size != len(manifest_bytes):
        raise OCIReviewRejected('Image manifest length mismatch')
    manifest, measured = _read(manifest_bytes, digest=child_digest,
                               allowed=(MANIFEST, DOCKER_MANIFEST))
    descriptor, config_size = _descriptor(manifest.get('config'),
                                           (CONFIG, DOCKER_CONFIG))
    if type(config_bytes) is not bytes or config_size != len(config_bytes):
        raise OCIReviewRejected('Config blob length mismatch')
    layers = manifest.get('layers')
    if type(layers) is not list or not 1 <= len(layers) <= MAX_LAYERS:
        raise OCIReviewRejected('Missing or excessive OCI layers')
    layer_digests = []
    for layer in layers:
        ldigest, _ = _descriptor(layer, LAYERS)
        if ldigest in layer_digests:
            raise OCIReviewRejected('Duplicate layer descriptor')
        layer_digests.append(ldigest)
    config, config_hash = _read_config(config_bytes, descriptor)
    if config.get('os') != 'linux' or config.get('architecture') != 'amd64':
        raise OCIReviewRejected('Image config platform mismatch')
    rootfs = config.get('rootfs')
    diff_ids = rootfs.get('diff_ids') if type(rootfs) is dict else None
    if (type(rootfs) is not dict or rootfs.get('type') != 'layers'
            or type(diff_ids) is not list or len(diff_ids) != len(layers)
            or any(type(d) is not str or SHA.fullmatch(d) is None for d in diff_ids)):
        raise OCIReviewRejected('Config lacks matching uncompressed layer digests')
    return {
        'schema': 1, 'kind': 'oci_manifest_chain_review',
        'index_digest': actual, 'platform_manifest_digest': measured,
        'config_digest': config_hash, 'layer_descriptor_count': len(layers),
        'index_to_config_digests_verified': True,
        'compressed_layer_bytes_verified': False,
        'publisher_signature_verified': False,
        'build_provenance_attestation_verified': False,
        'sbom_attestation_verified': False,
        'independent_pin_origin_verified': False,
        'runtime_execution_admitted': False,
        'customer_source_authorized': False,
        'delivery_authorized': False,
    }


def _read_config(raw, advertised):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_METADATA:
        raise OCIReviewRejected('Missing image config')
    actual = 'sha256:' + hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, advertised):
        raise OCIReviewRejected('Image config digest mismatch')
    try:
        obj = _strict_json(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise OCIReviewRejected('Malformed image config') from None
    if type(obj) is not dict:
        raise OCIReviewRejected('Invalid image config')
    return obj, actual
