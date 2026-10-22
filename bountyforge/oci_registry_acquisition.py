"""Read-only, anonymous Docker Hub metadata acquisition for the *fixed* image.

No layer downloads, image pulls, execution, credentials, redirects or
customer data. Returned evidence never authenticates the image publisher.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from .oci_runtime_provenance import (
    DOCKER_CONFIG, DOCKER_INDEX, DOCKER_MANIFEST, CONFIG, INDEX, MANIFEST,
    OCIReviewRejected, _digest, _strict_json, verify_pinned_image_reference,
)

_TOKEN_URL = ('https://auth.docker.io/token?service=registry.docker.io&'
              'scope=repository%3Alibrary%2Fpython%3Apull')
_REGISTRY = 'https://registry-1.docker.io/v2/library/python'
_ACCEPT = ', '.join((INDEX, DOCKER_INDEX, MANIFEST, DOCKER_MANIFEST))
_METADATA_LIMIT = 2 * 1024 * 1024


class RegistryEvidenceUnavailable(ValueError):
    """No trustworthy bounded registry response was available."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RegistryEvidenceUnavailable('Registry redirect rejected')


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _read(url, *, token=None, max_bytes=_METADATA_LIMIT, opener):
    headers = {'Accept': _ACCEPT, 'User-Agent': 'BountyForge-Anonymous-OCI-Review/1'}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with opener.open(req, timeout=12) as response:
            if response.status != 200:
                raise RegistryEvidenceUnavailable('Registry response status rejected')
            declared = response.headers.get('Content-Length')
            if declared is not None:
                if not declared.isdecimal() or int(declared) > max_bytes:
                    raise RegistryEvidenceUnavailable('Registry content length exceeded')
            data = response.read(max_bytes + 1)
            if not data or len(data) > max_bytes:
                raise RegistryEvidenceUnavailable('Missing or oversized registry response')
            return data
    except RegistryEvidenceUnavailable:
        raise
    except (OSError, ValueError, urllib.error.HTTPError):
        raise RegistryEvidenceUnavailable('Registry request unavailable') from None


def _valid_token(raw):
    try:
        value = _strict_json(raw)
    except (ValueError, UnicodeError):
        raise RegistryEvidenceUnavailable('Invalid registry token reply') from None
    token = value.get('token') if type(value) is dict else None
    if (type(token) is not str or not 16 <= len(token) <= 8192
            or not token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in token)):
        raise RegistryEvidenceUnavailable('Invalid anonymous registry token')
    return token


def acquire_pinned_python_metadata(index_pin, *, opener=None):
    """Acquire and verify actual index, amd64 child manifest and config.

    The pin is supplied by *trusted* application policy, not the registry.
    This routine is intentionally unable to authorize a runtime.
    """
    try:
        pin = _digest(index_pin)
        client = opener if opener is not None else _opener()
        token = _valid_token(_read(_TOKEN_URL, max_bytes=16_384, opener=client))
        index = _read(_REGISTRY + '/manifests/' + pin, token=token, opener=client)
        if 'sha256:' + hashlib.sha256(index).hexdigest() != pin:
            raise RegistryEvidenceUnavailable('Pinned index bytes differ')
        obj = _strict_json(index)
        if type(obj) is not dict:
            raise RegistryEvidenceUnavailable('Pinned registry object malformed')
        if obj.get('mediaType') in (INDEX, DOCKER_INDEX):
            manifests = obj.get('manifests')
            if type(manifests) is not list or not 1 <= len(manifests) <= 64:
                raise RegistryEvidenceUnavailable('Manifest descriptor set invalid')
            platform = [m for m in manifests if type(m) is dict
                        and type(m.get('platform')) is dict
                        and m['platform'].get('os') == 'linux'
                        and m['platform'].get('architecture') == 'amd64']
            if len(platform) != 1:
                raise RegistryEvidenceUnavailable('Unique amd64 child missing')
            child = _digest(platform[0].get('digest'))
            manifest = _read(_REGISTRY + '/manifests/' + child, token=token, opener=client)
            if 'sha256:' + hashlib.sha256(manifest).hexdigest() != child:
                raise RegistryEvidenceUnavailable('Child manifest digest mismatch')
        elif obj.get('mediaType') in (MANIFEST, DOCKER_MANIFEST):
            manifest = index
        else:
            raise RegistryEvidenceUnavailable('Unsupported OCI reference type')
        desc = _strict_json(manifest)
        if type(desc) is not dict or type(desc.get('config')) is not dict:
            raise RegistryEvidenceUnavailable('Image configuration descriptor missing')
        confighash = _digest(desc['config'].get('digest'))
        config = _read(_REGISTRY + '/blobs/' + confighash, token=token, opener=client)
        checked = verify_pinned_image_reference(
            index, manifest, config, expected_reference_digest=pin)
        return {
            **checked, 'source': 'anonymous_docker_hub_library_python',
            'acquired_over_https': True,
            'registry_domain_fixed': True,
            'actual_index_manifest_config_bytes_verified': True,
            'compressed_layer_bytes_verified': False,
            'publisher_signature_verified': False,
            'attestation_verified': False,
            'runtime_execution_admitted': False,
        }
    except (RegistryEvidenceUnavailable, OCIReviewRejected):
        raise RegistryEvidenceUnavailable('Pinned OCI metadata not authenticated') from None
    except (TypeError, KeyError, AttributeError, ValueError, RecursionError,
            OSError, UnicodeError):
        raise RegistryEvidenceUnavailable('Pinned OCI acquisition unavailable') from None
