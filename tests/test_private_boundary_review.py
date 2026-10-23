"""Owned Docker proof tamper/authorization negative regressions."""
import unittest
from bountyforge.curated_docker import IMAGE
from bountyforge.private_boundary_review import (
 CONTROLS, OwnedBoundaryRejected, review_owned_docker_proof,
 compare_review_only_custody)

def valid_proof():
    return {**{k:True for k in CONTROLS},
      'image_digest':IMAGE.split('@',1)[1], 'untrusted_execution_certified':False,
      'pid_current_at_denial':64,'pid_denial_events':2,
      'probe_threads':51,'cpu_throttled_periods':2,
      'cpu_pressure_wall_seconds':3.0,'cpu_pressure_used_seconds':2.8,
      'output':'secret source 123', 'host_path':'/private/customer.py'}

class OwnedDockerProofTests(unittest.TestCase):
    def test_verified_owned_proof_still_does_not_admit_customer_code(self):
        out=review_owned_docker_proof(valid_proof())
        self.assertEqual(out['control_count'],len(CONTROLS))
        self.assertTrue(out['owned_resource_pressure_verified'])
        self.assertFalse(out['private_execution_admitted'])
        self.assertFalse(out['private_custody_authorized'])
        self.assertNotIn('secret source',str(out))
        self.assertNotIn('customer.py',str(out))
    def test_all_controls_are_mandatory_and_strict_boolean(self):
        for key in CONTROLS:
            for value in (None,False,1,'true'):
                with self.subTest(key=key,value=value):
                    x=valid_proof(); x[key]=value
                    with self.assertRaises(OwnedBoundaryRejected):
                        review_owned_docker_proof(x)
    def test_wrong_image_and_fake_certification_rejected(self):
        for delta in ({'image_digest':'sha256:'+'0'*64},
                      {'image_digest':'latest'},
                      {'untrusted_execution_certified':True}):
            with self.subTest(delta=delta),self.assertRaises(OwnedBoundaryRejected):
                review_owned_docker_proof({**valid_proof(),**delta})
    def test_missing_resource_pressure_fails_closed(self):
        for name,value in [('pid_denial_events',0),('probe_threads',0),
                           ('pid_current_at_denial',65),('cpu_throttled_periods',0),
                           ('cpu_pressure_wall_seconds',float('nan')),
                           ('cpu_pressure_used_seconds',19)]:
            with self.subTest(name=name),self.assertRaises(OwnedBoundaryRejected):
                review_owned_docker_proof({**valid_proof(),name:value})
    def test_private_custody_flags_never_create_execution_capability(self):
        owned=review_owned_docker_proof(valid_proof())
        claimed={'kind':'private_custody_snapshot_verified',
                 'source_sha256':'a'*64,'tests_sha256':'b'*64,
                 'signed_scope_matched':True,'review_lease_validated':True,
                 'hashes_verified':True,'execution_authorized':True,
                 'fresh_payment_verified':True}
        output=compare_review_only_custody(owned,claimed)
        self.assertTrue(output['private_custody_metadata_present'])
        self.assertTrue(output['not_ready'])
        self.assertFalse(output['private_execution_admitted'])
        self.assertFalse(output['fresh_payment_verified'])
        self.assertFalse(output['private_custody_reopened_in_container'])
    def test_bad_custody_and_forged_boundary_rejected(self):
        b=review_owned_docker_proof(valid_proof())
        for item in (None,{}, {'source_sha256':True,'tests_sha256':'b'*64}):
            with self.assertRaises(OwnedBoundaryRejected):
                compare_review_only_custody(b,item)
        with self.assertRaises(OwnedBoundaryRejected):
            compare_review_only_custody({'kind':'fake'},{})

if __name__=='__main__': unittest.main()
