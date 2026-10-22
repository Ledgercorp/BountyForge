"""No network, no extraction and no execution for bounded layer hash review."""
import gzip
import hashlib
import io
import unittest
from unittest.mock import patch

from bountyforge.oci_layer_digest import hash_bounded_gzip_layer
from bountyforge.oci_runtime_provenance import OCIReviewRejected


def sample(message=b'layer-data'*100):
    data=gzip.compress(message, mtime=0)
    desc={'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip',
          'digest':'sha256:'+hashlib.sha256(data).hexdigest(),
          'size':len(data)}
    diff='sha256:'+hashlib.sha256(message).hexdigest()
    return data,desc,diff


class BoundedLayerDigestTests(unittest.TestCase):
    def test_complete_gzip_layer_verifies_both_hashes_without_extraction(self):
        data,desc,diff=sample()
        report=hash_bounded_gzip_layer(io.BytesIO(data),desc,diff)
        self.assertEqual(report['compressed_bytes'],len(data))
        self.assertEqual(report['compressed_digest'],desc['digest'])
        self.assertEqual(report['diff_id'],diff)
        self.assertEqual(report['uncompressed_bytes'],len(b'layer-data'*100))

    def test_corrupt_compressed_bytes_rejected(self):
        data,desc,diff=sample()
        bad=bytearray(data);bad[-8]^=1
        with self.assertRaises(OCIReviewRejected):
            hash_bounded_gzip_layer(io.BytesIO(bytes(bad)),desc,diff)

    def test_wrong_diffid_rejected(self):
        data,desc,diff=sample()
        with self.assertRaises(OCIReviewRejected):
            hash_bounded_gzip_layer(io.BytesIO(data),desc,'sha256:'+'0'*64)

    def test_truncated_or_trailing_gzip_rejected(self):
        data,desc,diff=sample()
        for bad in (data[:-1],data+b'additional',data+data):
            with self.subTest(size=len(bad)),self.assertRaises(OCIReviewRejected):
                hash_bounded_gzip_layer(io.BytesIO(bad),desc,diff)

    def test_decompression_bomb_budget_blocks_before_full_output(self):
        data,desc,diff=sample(b'A'*500000)
        with self.assertRaises(OCIReviewRejected):
            hash_bounded_gzip_layer(io.BytesIO(data),desc,diff,max_uncompressed=16000)

    def test_bad_compressed_size_or_type_rejected(self):
        data,desc,diff=sample()
        for changed in (dict(desc,size=len(data)-1),
                        dict(desc,mediaType='application/vnd.oci.image.layer.v1.tar+zstd'),
                        dict(desc,urls=['https://other.invalid/'])):
            with self.subTest(changed=changed),self.assertRaises(OCIReviewRejected):
                hash_bounded_gzip_layer(io.BytesIO(data),changed,diff)

    def test_stream_unexpected_object_and_io_failure_rejected(self):
        data,desc,diff=sample()
        class NonByteStream:
            def read(self,limit): return 'bad'
        with self.assertRaises(OCIReviewRejected):
            hash_bounded_gzip_layer(NonByteStream(),desc,diff)
        class IOFail:
            def read(self,limit): raise OSError('sensitive details')
        with self.assertRaises(OCIReviewRejected) as x:
            hash_bounded_gzip_layer(IOFail(),desc,diff)
        self.assertNotIn('sensitive',str(x.exception))

if __name__=='__main__':
    unittest.main()
