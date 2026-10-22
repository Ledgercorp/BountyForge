"""Read-only, anonymous Docker Hub metadata acquisition for the *fixed* image.

No layer downloads, image pulls, execution, credentials, redirects or
customer data. Returned evidence never authenticates the image publisher.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
import urllib.parse
import re
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
    def __init__(self, message, *, blocked_host=None):
        super().__init__(message)
        self.blocked_host = blocked_host


class _RestrictedBlobRedirect(urllib.request.HTTPRedirectHandler):
    """One TLS-only Docker Hub blob handoff; never forward bearer headers."""
    def __init__(self):
        super().__init__()
        self.used = False

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if self.used or code != 307 or request.get_method() != 'GET':
            raise RegistryEvidenceUnavailable('Unexpected Docker CDN redirect')
        origin = request.full_url
        prefix = _REGISTRY + '/blobs/sha256:'
        if not origin.startswith(prefix):
            raise RegistryEvidenceUnavailable('Redirect from unapproved registry resource')
        digest = origin[len(prefix):]
        if re.fullmatch('[0-9a-f]{64}', digest) is None:
            raise RegistryEvidenceUnavailable('Redirected blob digest malformed')
        dest = urllib.parse.urlsplit(newurl)
        host = dest.hostname or ''
        r2 = re.fullmatch(
            r'docker-images-prod\.[a-z0-9-]+\.r2\.cloudflarestorage\.com',
            host)
        s3 = re.fullmatch(
            r'docker-images-prod\.s3(?:\.[a-z0-9-]+)?\.amazonaws\.com',
            host)
        approved = host == 'production.cloudflare.docker.com' or r2 or s3
        if not approved:
            safe_host = host if re.fullmatch(r'[a-z0-9.-]{1,253}', host) else None
            raise RegistryEvidenceUnavailable(
                'Docker CDN host not allowlisted', blocked_host=safe_host)
        if (dest.scheme != 'https' or dest.port is not None
                or dest.username is not None or dest.password is not None
                or dest.fragment):
            raise RegistryEvidenceUnavailable('Docker CDN URL policy rejected')
        if digest not in dest.path:
            raise RegistryEvidenceUnavailable('Docker CDN digest path mismatch')
        self.used = True
        # A new Request without Authorization protects the Docker Hub token.
        return urllib.request.Request(
            newurl,
            headers={'User-Agent': 'BountyForge-Anonymous-OCI-Review/1'},
            method='GET')


def _opener():
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _RestrictedBlobRedirect())


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
    stage = 'reference_pin'
    try:
        pin = _digest(index_pin)
        client = opener if opener is not None else _opener()
        stage = 'anonymous_token'
        token = _valid_token(_read(_TOKEN_URL, max_bytes=16_384, opener=client))
        stage = 'pinned_reference'
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
            stage = 'platform_manifest'
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
        stage = 'config_blob'
        config = _read(_REGISTRY + '/blobs/' + confighash, token=token, opener=client)
        stage = 'metadata_chain'
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
    except (RegistryEvidenceUnavailable, OCIReviewRejected) as error:
        reasons = {
            'Docker CDN host not allowlisted': 'cdn_host',
            'Docker CDN URL policy rejected': 'cdn_url',
            'Docker CDN digest path mismatch': 'cdn_digest_path',
            'Unexpected Docker CDN redirect': 'cdn_redirect_count',
            'Registry request unavailable': 'transport',
            'Registry content length exceeded': 'oversize',
            'Missing or oversized registry response': 'empty_or_oversize',
            'Registry response status rejected': 'http_status',
            'Pinned image config digest mismatch': 'config_digest',
        }
        reason = reasons.get(str(error), 'invalid_metadata_or_unknown')
        raise RegistryEvidenceUnavailable(
            'Pinned OCI metadata blocked at ' + stage + ':' + reason,
            blocked_host=(error.blocked_host
                if isinstance(error, RegistryEvidenceUnavailable) else None)) from None
    except (TypeError, KeyError, AttributeError, ValueError, RecursionError,
            OSError, UnicodeError):
        raise RegistryEvidenceUnavailable('Pinned OCI acquisition blocked at ' + stage) from None
