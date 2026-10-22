"""Bounded owned-public Docker image layer digest review, no archive extraction.

Verifies compressed SHA-256 plus uncompressed gzip DiffIDs from the actual
fixed manifest. Still NOT image publisher authentication or execution admission.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import urllib.request
import zlib
from .oci_runtime_provenance import (
    MANIFEST, DOCKER_MANIFEST, CONFIG, DOCKER_CONFIG, LAYERS, OCIReviewRejected,
    _digest, _descriptor, _strict_json, verify_pinned_image_reference,
)
from .oci_registry_acquisition import (
    _TOKEN_URL, _REGISTRY, _opener, _read, _valid_token,
    RegistryEvidenceUnavailable,
)

CHUNK = 65536
MAX_LAYER_COMPRESSED = 96 * 1024 * 1024
MAX_TOTAL_COMPRESSED = 128 * 1024 * 1024
MAX_LAYER_UNCOMPRESSED = 384 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 768 * 1024 * 1024
_GZIP_MEDIA = frozenset({
    'application/vnd.docker.image.rootfs.diff.tar.gzip',
    'application/vnd.oci.image.layer.v1.tar+gzip',
})


def hash_bounded_gzip_layer(stream, descriptor, diff_id, *,
                            max_compressed=MAX_LAYER_COMPRESSED,
                            max_uncompressed=MAX_LAYER_UNCOMPRESSED):
    """Hash bounded *raw stream* and decompressed bytes without tar extraction."""
    compressed_digest, expected_size = _descriptor(descriptor, _GZIP_MEDIA)
    diff_id = _digest(diff_id)
    if (type(max_compressed) is not int or type(max_uncompressed) is not int
            or max_compressed < 1 or max_uncompressed < 1
            or expected_size > max_compressed):
        raise OCIReviewRejected('Compressed layer budget exceeded')
    zipped = hashlib.sha256()
    plain = hashlib.sha256()
    decoder = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
    compressed_bytes = 0
    uncompressed_bytes = 0
    try:
        while True:
            chunk = stream.read(min(CHUNK, expected_size + 1 - compressed_bytes))
            if type(chunk) is not bytes:
                raise OCIReviewRejected('Invalid compressed layer stream')
            if not chunk:
                break
            compressed_bytes += len(chunk)
            if compressed_bytes > expected_size:
                raise OCIReviewRejected('Compressed layer longer than manifest')
            zipped.update(chunk)
            pending = chunk
            while pending:
                before = len(pending)
                output = decoder.decompress(pending, CHUNK)
                pending = decoder.unconsumed_tail
                uncompressed_bytes += len(output)
                if uncompressed_bytes > max_uncompressed:
                    raise OCIReviewRejected('Uncompressed layer budget exceeded')
                plain.update(output)
                if pending and len(pending) == before and not output:
                    raise OCIReviewRejected('Stalled gzip decoder')
            if decoder.unused_data:
                raise OCIReviewRejected('Unexpected trailing compressed data')
        if compressed_bytes != expected_size or not decoder.eof or decoder.unused_data:
            raise OCIReviewRejected('Compressed layer truncated or malformed')
        actual_compressed = 'sha256:' + zipped.hexdigest()
        actual_plain = 'sha256:' + plain.hexdigest()
        if (not hmac.compare_digest(actual_compressed, compressed_digest)
                or not hmac.compare_digest(actual_plain, diff_id)):
            raise OCIReviewRejected('Layer compressed or DiffID hash mismatch')
        return {'compressed_digest':actual_compressed,'diff_id':actual_plain,
                'compressed_bytes':compressed_bytes,
                'uncompressed_bytes':uncompressed_bytes}
    except (OSError, zlib.error, ValueError, TypeError):
        raise OCIReviewRejected('Layer stream unavailable or malformed') from None


def verify_actual_pinned_python_layers(image_digest):
    """Retrieve ONLY the fixed public Python image; verify 4 expected gzip layers.

    This function is deliberately separate from automatic tests and must be
    called only for an approved one-shot public Docker Hub verification.
    """
    try:
        from .curated_docker import IMAGE
        pin = _digest(image_digest)
        if pin != IMAGE.split('@',1)[1]:
            raise OCIReviewRejected('Only currently pinned image is permitted')
        token = _valid_token(_read(_TOKEN_URL, max_bytes=16_384, opener=_opener()))
        image = _read(_REGISTRY + '/manifests/' + pin, token=token, opener=_opener())
        if 'sha256:' + hashlib.sha256(image).hexdigest() != pin:
            raise OCIReviewRejected('Pinned image manifest differs')
        manifest = _strict_json(image)
        if type(manifest) is not dict or manifest.get('mediaType') not in (
                MANIFEST,DOCKER_MANIFEST):
            raise OCIReviewRejected('Pinned platform manifest type required')
        descriptor = manifest.get('config')
        cfgsha, cfgsize = _descriptor(descriptor, (CONFIG,DOCKER_CONFIG))
        config = _read(_REGISTRY+'/blobs/'+cfgsha, token=token, opener=_opener())
        if len(config) != cfgsize:
            raise OCIReviewRejected('Config length differs from manifest')
        verified = verify_pinned_image_reference(
            image, image, config, expected_reference_digest=pin)
        conf = _strict_json(config)
        layers = manifest['layers']
        if len(layers) != verified['layer_descriptor_count']:
            raise OCIReviewRejected('Layer count inconsistent')
        diffs = conf['rootfs']['diff_ids']
        total_zipped = sum(_descriptor(d,_GZIP_MEDIA)[1] for d in layers)
        if total_zipped > MAX_TOTAL_COMPRESSED:
            raise OCIReviewRejected('Image compressed budget exceeded')
        proofs = []
        expanded = 0
        for d,unpacked in zip(layers,diffs):
            digest, expected_bytes = _descriptor(d,_GZIP_MEDIA)
            if expected_bytes > MAX_LAYER_COMPRESSED:
                raise OCIReviewRejected('Image layer exceeds compressed budget')
            req = urllib.request.Request(
                _REGISTRY+'/blobs/'+digest,
                headers={'Authorization':'Bearer '+token,
                         'User-Agent':'BountyForge-Anonymous-OCI-Review/1'},
                method='GET')
            try:
                with _opener().open(req,timeout=25) as response:
                    if response.status != 200:
                        raise OCIReviewRejected('Docker layer retrieval status rejected')
                    proof = hash_bounded_gzip_layer(
                        response,d,unpacked,
                        max_uncompressed=min(MAX_LAYER_UNCOMPRESSED,
                                             MAX_TOTAL_UNCOMPRESSED-expanded))
            except (OSError,ValueError,TypeError):
                raise OCIReviewRejected('Docker layer could not be verified') from None
            expanded += proof['uncompressed_bytes']
            if expanded > MAX_TOTAL_UNCOMPRESSED:
                raise OCIReviewRejected('Uncompressed image total exceeded')
            proofs.append(proof)
        return {
            'kind':'public_python_layer_content_review',
            'pinned_manifest_digest':pin,
            'config_digest':verified['config_digest'],
            'compressed_layers_verified':len(proofs),
            'compressed_bytes_verified':sum(p['compressed_bytes'] for p in proofs),
            'uncompressed_bytes_verified':expanded,
            'all_compressed_layer_hashes_verified':True,
            'all_uncompressed_diffids_verified':True,
            'independent_publisher_signature_verified':False,
            'build_provenance_attestation_verified':False,
            'sbom_signature_verified':False,
            'runtime_execution_admitted':False,
            'customer_source_authorized':False,
            'delivery_authorized':False,
        }
    except (OCIReviewRejected,RegistryEvidenceUnavailable):
        raise OCIReviewRejected('Actual pinned image layer review blocked') from None
