"""No-network tests for one-shot pinned layer observation."""
import unittest
from unittest.mock import patch

from scripts import check_pinned_layers as runner
from bountyforge.oci_runtime_provenance import OCIReviewRejected


class PublicLayerObservationTests(unittest.TestCase):
    def test_only_pinned_image_and_verified_digest_fields_reported(self):
        report={'pinned_manifest_digest':'sha256:'+'a'*64,'config_digest':'sha256:'+'b'*64,
                'compressed_layers_verified':4,'compressed_bytes_verified':200,
                'uncompressed_bytes_verified':300,
                'all_compressed_layer_hashes_verified':True,
                'all_uncompressed_diffids_verified':True,
                'runtime_execution_admitted':False}
        with patch.object(runner,'verify_actual_pinned_python_layers',return_value=report) as stub:
            result=runner.run_review()
        self.assertEqual(stub.call_args.args[0],runner.IMAGE.split('@',1)[1])
        self.assertEqual(result['result'],'ALL_LAYER_HASHES_VERIFIED')
        self.assertEqual(result['compressed_layers_verified'],4)
        self.assertFalse(result['private_execution_authorized'])
        self.assertFalse(result['publisher_trust_admitted'])

    def test_failures_are_sanitized_and_never_admitted(self):
        with patch.object(runner,'verify_actual_pinned_python_layers',
                          side_effect=OCIReviewRejected('SECRET CDN token')):
            result=runner.run_review()
        self.assertEqual(result['result'],'LAYER_REVIEW_UNVERIFIED')
        self.assertFalse(result['all_compressed_layer_hashes_verified'])
        self.assertFalse(result['private_execution_authorized'])
        self.assertNotIn('SECRET',str(result))

if __name__=='__main__':
    unittest.main()
