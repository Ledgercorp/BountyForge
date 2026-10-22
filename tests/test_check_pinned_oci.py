"""No external network during unit tests for one-shot public metadata output."""
import unittest
from unittest.mock import patch
from scripts import check_pinned_oci as runner
from bountyforge.oci_registry_acquisition import RegistryEvidenceUnavailable

class PinnedOCIObserverTests(unittest.TestCase):
    def test_success_reports_only_hashes_and_non_admission(self):
        digest = 'sha256:'+'a'*64
        sample = {'index_digest':digest,'platform_manifest_digest':digest,
                  'config_digest':digest,'layer_descriptor_count':5}
        with patch.object(runner,'acquire_pinned_python_metadata',return_value=sample) as action:
            receipt=runner.check()
        self.assertEqual(receipt['result'],'METADATA_HASHES_VERIFIED')
        self.assertEqual(receipt['index_digest'],digest)
        self.assertEqual(action.call_args.args[0],runner.IMAGE.split('@',1)[1])
        self.assertFalse(receipt['runtime_execution_admitted'])
        self.assertFalse(receipt['compressed_layer_bytes_verified'])

    def test_remote_error_is_redacted_and_not_admitted(self):
        with patch.object(runner,'acquire_pinned_python_metadata',
                          side_effect=RegistryEvidenceUnavailable('Bearer private-token')):
            receipt=runner.check()
        self.assertEqual(receipt['result'],'UNAVAILABLE_OR_UNVERIFIED')
        self.assertNotIn('private-token',str(receipt))
        self.assertFalse(receipt['commercial_fulfillment_authorized'])

if __name__=='__main__':
    unittest.main()
