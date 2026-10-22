"""Synthetic, no-network acquisition tests for exact Docker Hub metadata."""
import hashlib
import json
import unittest
from unittest.mock import Mock

from bountyforge.oci_registry_acquisition import (
    RegistryEvidenceUnavailable, _REGISTRY, _TOKEN_URL,
    acquire_pinned_python_metadata,
)
from test_oci_runtime_provenance import blob, descriptor, fixture
from bountyforge.oci_runtime_provenance import INDEX


class Response:
    def __init__(self, payload, status=200, declared=None):
        self.payload = payload
        self.status = status
        self.headers = {'Content-Length': str(len(payload)) if declared is None else declared}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, count):
        return self.payload[:count]


class Opener:
    def __init__(self, mapping):
        self.mapping = mapping
        self.urls = []
        self.auth_headers = []
    def open(self, req, timeout):
        self.urls.append(req.full_url)
        self.auth_headers.append(req.get_header('Authorization'))
        if req.full_url not in self.mapping:
            raise OSError('Forbidden test URL: '+req.full_url)
        result = self.mapping[req.full_url]
        if isinstance(result, BaseException):
            raise result
        return result


def setup():
    index, manifest, config = fixture()
    pin = descriptor(index, INDEX)['digest']
    contents = json.loads(index)
    child = contents['manifests'][0]['digest']
    cfg = json.loads(manifest)['config']['digest']
    urls = [_TOKEN_URL, _REGISTRY + '/manifests/' + pin,
            _REGISTRY + '/manifests/' + child, _REGISTRY + '/blobs/' + cfg]
    mapping = dict(zip(urls, [Response(b'{"token":"'+b'x'*24+b'"}'),
                             Response(index), Response(manifest), Response(config)]))
    return pin, Opener(mapping), urls


class RegistryAcquisitionTests(unittest.TestCase):
    def test_all_requests_fixed_and_digest_chain_checked_without_authority(self):
        pin, opener, urls = setup()
        result = acquire_pinned_python_metadata(pin, opener=opener)
        self.assertEqual(opener.urls, urls)
        self.assertIsNone(opener.auth_headers[0])
        self.assertEqual(opener.auth_headers[1:], ['Bearer ' + 'x'*24]*3)
        self.assertEqual(result['index_digest'], pin)
        self.assertTrue(result['actual_index_manifest_config_bytes_verified'])
        self.assertFalse(result['compressed_layer_bytes_verified'])
        self.assertFalse(result['publisher_signature_verified'])
        self.assertFalse(result['runtime_execution_admitted'])
        self.assertNotIn('Bearer ', str(result))
        self.assertNotIn('x'*24, str(result))


    def test_direct_pinned_manifest_uses_three_requests_and_no_index_lookup(self):
        index, manifest, config=fixture()
        from bountyforge.oci_runtime_provenance import MANIFEST
        pin=descriptor(manifest,MANIFEST)['digest']
        config_digest=json.loads(manifest)['config']['digest']
        urls=[_TOKEN_URL,_REGISTRY+'/manifests/'+pin,
              _REGISTRY+'/blobs/'+config_digest]
        opener=Opener(dict(zip(urls,[
            Response(b'{"token":"'+b'x'*24+b'"}'),
            Response(manifest),Response(config)])))
        evidence=acquire_pinned_python_metadata(pin,opener=opener)
        self.assertEqual(opener.urls,urls)
        self.assertEqual(evidence['pinned_reference_kind'],'linux_amd64_manifest')
        self.assertEqual(evidence['pinned_reference_digest'],pin)
        self.assertFalse(evidence['publisher_signature_verified'])

    def test_registry_supplied_wrong_index_bytes_rejected(self):
        pin, opener, urls = setup()
        opener.mapping[urls[1]] = Response(b'{"tampered":true}')
        with self.assertRaises(RegistryEvidenceUnavailable):
            acquire_pinned_python_metadata(pin, opener=opener)

    def test_mutated_config_and_child_rejected(self):
        for index in (2, 3):
            pin, opener, urls = setup()
            opener.mapping[urls[index]] = Response(b'{"substituted":true}')
            with self.subTest(index=index), self.assertRaises(RegistryEvidenceUnavailable):
                acquire_pinned_python_metadata(pin, opener=opener)

    def test_token_response_missing_or_invalid(self):
        for raw in (b'{}', b'{"token": 1}', b'{"token":"short"}', b'invalid', b'{"token":" bad token "}',
                    b'{"token":"x","token":"y"}'):
            pin, opener, urls = setup()
            opener.mapping[urls[0]] = Response(raw)
            # Ambiguous JSON token keys must be rejected.
            with self.subTest(raw=raw):
                try:
                    acquire_pinned_python_metadata(pin, opener=opener)
                except RegistryEvidenceUnavailable:
                    continue
                self.fail('Malformed token unexpectedly accepted')

    def test_status_and_declared_size_rejected(self):
        for wrong in (Response(b'foo',status=302), Response(b'foo',declared='999999999'),
                      Response(b'foo',declared='bogus')):
            pin, opener, urls = setup()
            opener.mapping[urls[0]] = wrong
            with self.assertRaises(RegistryEvidenceUnavailable):
                acquire_pinned_python_metadata(pin, opener=opener)

    def test_registry_endpoint_failure_sanitized(self):
        pin, opener, urls = setup()
        opener.mapping[urls[2]] = OSError('private token and URL')
        with self.assertRaises(RegistryEvidenceUnavailable) as found:
            acquire_pinned_python_metadata(pin, opener=opener)
        self.assertNotIn('private token', str(found.exception))
        self.assertIn('platform_manifest', str(found.exception))

    def test_pin_is_required_and_never_accepted_from_remote_tag(self):
        for bad in ('latest','sha256:'+'0'*64, 'sha256:'+'A'*64, None):
            pin, opener, urls = setup()
            with self.subTest(pin=bad), self.assertRaises(RegistryEvidenceUnavailable):
                acquire_pinned_python_metadata(bad, opener=opener)
        self.assertFalse(any('/tags/' in s for s in opener.urls))

if __name__ == '__main__':
    unittest.main()
