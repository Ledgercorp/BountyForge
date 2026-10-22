import hashlib
import json
import unittest
from copy import deepcopy
from bountyforge.oci_runtime_provenance import (
    CONFIG, INDEX, MANIFEST, OCIReviewRejected, verify_oci_manifest_chain, verify_pinned_image_reference)


def blob(d):
    return json.dumps(d, sort_keys=True, separators=(',', ':')).encode()


def descriptor(content, media):
    return {'mediaType': media, 'digest': 'sha256:' + hashlib.sha256(content).hexdigest(),
            'size': len(content)}


def fixture():
    rawconfig = blob({'os': 'linux', 'architecture': 'amd64',
                      'rootfs': {'type': 'layers', 'diff_ids': ['sha256:' + '3' * 64]}})
    layer = {'mediaType': 'application/vnd.oci.image.layer.v1.tar+gzip',
             'digest': 'sha256:' + '4' * 64, 'size': 512}
    rawmanifest = blob({'schemaVersion': 2, 'mediaType': MANIFEST,
                        'config': descriptor(rawconfig, CONFIG), 'layers': [layer]})
    rawindex = blob({'schemaVersion': 2, 'mediaType': INDEX, 'manifests': [{
        **descriptor(rawmanifest, MANIFEST),
        'platform': {'os': 'linux', 'architecture': 'amd64'}}]})
    return rawindex, rawmanifest, rawconfig


def review(*raw):
    return verify_oci_manifest_chain(*raw, expected_index_digest=descriptor(raw[0], INDEX)['digest'])


class OCIProvenanceTests(unittest.TestCase):
    def test_valid_synthetic_chain_never_grants_execution_or_publisher_trust(self):
        result = review(*fixture())
        self.assertEqual(result['layer_descriptor_count'], 1)
        self.assertTrue(result['index_to_config_digests_verified'])
        for key in ('compressed_layer_bytes_verified', 'publisher_signature_verified',
                    'build_provenance_attestation_verified', 'sbom_attestation_verified',
                    'independent_pin_origin_verified', 'runtime_execution_admitted',
                    'customer_source_authorized', 'delivery_authorized'):
            self.assertIs(result[key], False)
        self.assertNotIn('rootfs', str(result))

    def test_index_pin_mismatch_rejected(self):
        with self.assertRaises(OCIReviewRejected):
            verify_oci_manifest_chain(*fixture(), expected_index_digest='sha256:' + '0'*64)

    def test_config_mutation_and_manifest_mutation_rejected(self):
        index, man, cfg = fixture()
        with self.assertRaises(OCIReviewRejected): review(index, man+b' ', cfg)
        with self.assertRaises(OCIReviewRejected): review(index, man, cfg+b' ')

    def test_rejects_fake_platform_duplicates(self):
        i,m,c = fixture()
        index = json.loads(i)
        index['manifests'].append(deepcopy(index['manifests'][0]))
        with self.assertRaises(OCIReviewRejected):review(blob(index),m,c)

    def test_bad_architecture_or_fake_index_schema_rejected(self):
        i,m,c = fixture()
        for field,value in [('schemaVersion', 1), ('mediaType', 'attestation-only')]:
            index = json.loads(i);index[field]=value
            with self.assertRaises(OCIReviewRejected):review(blob(index),m,c)
        config=json.loads(c);config['architecture']='arm64'
        updated=blob(config)
        mdata=json.loads(m);mdata['config']=descriptor(updated,CONFIG)
        updatedm=blob(mdata)
        idata=json.loads(i);idata['manifests'][0].update(descriptor(updatedm,MANIFEST))
        with self.assertRaises(OCIReviewRejected):review(blob(idata),updatedm,updated)

    def test_nonstring_layer_media_type_rejected_without_typeerror(self):
        i,m,c=fixture()
        document=json.loads(m)
        document['layers'][0]['mediaType']=['unexpected']
        child=blob(document)
        index=json.loads(i)
        index['manifests'][0].update(descriptor(child,MANIFEST))
        with self.assertRaises(OCIReviewRejected):review(blob(index),child,c)

    def test_rejects_remote_blob_urls(self):
        i,m,c=fixture(); data=json.loads(m)
        data['layers'][0]['urls']=['https://example.invalid/key']
        m2=blob(data); idx=json.loads(i);idx['manifests'][0].update(descriptor(m2,MANIFEST))
        with self.assertRaises(OCIReviewRejected):review(blob(idx),m2,c)

    def test_duplicate_layer_and_missing_diffids_rejected(self):
        i,m,c=fixture()
        doc=json.loads(m);doc['layers'].append(doc['layers'][0])
        m2=blob(doc);idx=json.loads(i);idx['manifests'][0].update(descriptor(m2,MANIFEST))
        with self.assertRaises(OCIReviewRejected):review(blob(idx),m2,c)
        badcfg=json.loads(c);badcfg['rootfs']['diff_ids']=[]
        cb=blob(badcfg);doc=json.loads(m);doc['config']=descriptor(cb,CONFIG)
        m2=blob(doc);idx=json.loads(i);idx['manifests'][0].update(descriptor(m2,MANIFEST))
        with self.assertRaises(OCIReviewRejected):review(blob(idx),m2,cb)

    def test_duplicate_json_keys_and_wrong_blob_types_rejected(self):
        i,m,c=fixture()
        with self.assertRaises(OCIReviewRejected):
            review(b'{"schemaVersion":2,"schemaVersion":2,"mediaType":"'+INDEX.encode()+b'","manifests":[]}', m, c)
        with self.assertRaises(OCIReviewRejected):review(i, None, c)
        with self.assertRaises(OCIReviewRejected):review(i, m, None)

    def test_malformed_digest_and_nontyped_metadata_rejected(self):
        i,m,c=fixture()
        for digest in ('sha256:'+'F'*64, 'md5:'+'0'*32, 'sha256:'+'a'*63, None, True):
            with self.subTest(digest=digest), self.assertRaises(OCIReviewRejected):
                verify_oci_manifest_chain(i,m,c, expected_index_digest=digest)
        with self.assertRaises(OCIReviewRejected):review(i,m,b'not JSON')
        with self.assertRaises(OCIReviewRejected):review(i,m,c+b'x'*(2*1024*1024))

    def test_directly_pinned_amd64_manifest_and_existing_index_both_verify(self):
        index, manifest, config = fixture()
        direct_pin=descriptor(manifest, MANIFEST)['digest']
        verified=verify_pinned_image_reference(
            manifest,manifest,config,expected_reference_digest=direct_pin)
        self.assertEqual(verified['pinned_reference_kind'],'linux_amd64_manifest')
        self.assertEqual(verified['pinned_reference_digest'],direct_pin)
        self.assertTrue(verified['pinned_reference_to_config_digests_verified'])
        self.assertIsNone(verified['index_digest'])
        self.assertFalse(verified['runtime_execution_admitted'])
        multi=verify_pinned_image_reference(
            index,manifest,config,
            expected_reference_digest=descriptor(index, INDEX)['digest'])
        self.assertEqual(multi['pinned_reference_kind'],'multi_platform_index')

    def test_direct_manifest_mismatch_or_substitution_is_rejected(self):
        _,manifest,config=fixture()
        pin=descriptor(manifest,MANIFEST)['digest']
        for parts in ((manifest,manifest+b' ',config),
                      (manifest,manifest,config+b' '),
                      (manifest+b' ',manifest+b' ',config)):
            with self.subTest(size=len(parts[0])),self.assertRaises(OCIReviewRejected):
                verify_pinned_image_reference(*parts,expected_reference_digest=pin)
        wrong=json.loads(config);wrong['architecture']='arm64'
        cb=blob(wrong);m=json.loads(manifest);m['config']=descriptor(cb,CONFIG)
        newer=blob(m)
        with self.assertRaises(OCIReviewRejected):
            verify_pinned_image_reference(newer,newer,cb,
                expected_reference_digest=descriptor(newer,MANIFEST)['digest'])

if __name__ == '__main__': unittest.main()
