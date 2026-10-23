"""Mock verifier boundaries but never mock an execution admission."""
import sys
import types
import unittest
from unittest.mock import patch

from bountyforge import private_job_contract as job

DIGEST = 'sha256:' + 'a'*64
BASIC = {'snapshot_sha256':'b'*64, 'lease_fence':3,
         'source_sha256':'c'*64, 'tests_sha256':'d'*64,
         'signed_scope_matched':True,'review_lease_validated':True,
         'hashes_verified':True}


def stubs():
    curated = types.ModuleType('bountyforge.curated_docker')
    curated.IMAGE = 'python@' + DIGEST
    custody = types.ModuleType('bountyforge.private_source_custody')
    custody.PrivateSourceRejected = type('PrivateSourceRejected',(ValueError,),{})
    custody.verify_recorded_private_snapshot = lambda *a,**kw:dict(BASIC)
    boundary = types.ModuleType('bountyforge.private_boundary_review')
    boundary.OwnedBoundaryRejected=type('OwnedBoundaryRejected',(ValueError,),{})
    boundary.review_owned_docker_proof=lambda proof:{'docker_image_digest':DIGEST}
    return {'bountyforge.curated_docker':curated,
            'bountyforge.private_source_custody':custody,
            'bountyforge.private_boundary_review':boundary}


def call():
    return job.review_private_job_prerequisites(
        '/private-snapshot',object(),'fake-session',token='sensitive-lease',
        expected_fence=3,now=42,owned_docker_proof={'forged':True},
        oci_index=b'owned-index',oci_manifest=b'owned-manifest',oci_config=b'owned-config')


class PrivateJobContractTests(unittest.TestCase):
    def setUp(self):
        self.mocked=patch.dict(sys.modules,stubs())
        self.mocked.start();self.addCleanup(self.mocked.stop)
        self.proof=patch.object(job,'verify_pinned_image_reference',return_value={
            'pinned_reference_digest':DIGEST,
            'pinned_reference_kind':'linux_amd64_manifest',
            'publisher_signature_verified':False,
            'runtime_execution_admitted':False})
        self.proof.start();self.addCleanup(self.proof.stop)

    def test_all_reviewable_metadata_still_not_admitted(self):
        r=call()
        self.assertEqual(r['status'],'REVIEWED_NOT_ADMITTED')
        self.assertTrue(r['current_signed_custody_reverified'])
        self.assertTrue(r['oci_pinned_reference_to_config_digests_verified'])
        self.assertGreaterEqual(len(r['blocking_requirements']),7)
        for k in ('customer_source_authorized','execution_authorized',
                  'delivery_authorized','fresh_payment_verified',
                  'private_code_executed','source_shared_with_model'):
            self.assertIs(r[k],False)
        self.assertNotIn('sensitive-lease',str(r))
        self.assertNotIn('/private-snapshot',str(r))

    def test_provenance_is_bound_to_fixed_docker_image_digest(self):
        from bountyforge.private_job_contract import verify_pinned_image_reference
        call()
        args=verify_pinned_image_reference.call_args.kwargs
        self.assertEqual(args['expected_reference_digest'],DIGEST)

    def test_failed_current_custody_and_revocation_do_not_pass(self):
        mod=sys.modules['bountyforge.private_source_custody']
        mod.verify_recorded_private_snapshot=lambda *a,**kw: (_ for _ in ()).throw(mod.PrivateSourceRejected('secret access'))
        with self.assertRaises(job.PrivateJobReviewBlocked) as caught:call()
        self.assertNotIn('secret access',str(caught.exception))

    def test_rechecked_custody_change_fails(self):
        mod=sys.modules['bountyforge.private_source_custody']
        sequence=iter([dict(BASIC),dict(BASIC,snapshot_sha256='e'*64)])
        mod.verify_recorded_private_snapshot=lambda *a,**kw:next(sequence)
        with self.assertRaises(job.PrivateJobReviewBlocked):call()

    def test_wrong_docker_image_fails(self):
        mod=sys.modules['bountyforge.private_boundary_review']
        mod.review_owned_docker_proof=lambda _: {'docker_image_digest':'sha256:'+'0'*64}
        with self.assertRaises(job.PrivateJobReviewBlocked):call()

    def test_wrong_verified_index_digest_cannot_be_accepted(self):
        job.verify_pinned_image_reference.return_value={
            'pinned_reference_digest':'sha256:'+'0'*64,
            'publisher_signature_verified':False,
            'runtime_execution_admitted':False}
        with self.assertRaises(job.PrivateJobReviewBlocked):call()

    def test_missing_or_spoofed_provenance_rejected(self):
        job.verify_pinned_image_reference.return_value={'pinned_reference_digest':DIGEST,
            'pinned_reference_kind':'linux_amd64_manifest',
                    'publisher_signature_verified':True,
                    'runtime_execution_admitted':True}
        with self.assertRaises(job.PrivateJobReviewBlocked):call()
        job.verify_pinned_image_reference.side_effect=job.OCIReviewRejected('secret source')
        with self.assertRaises(job.PrivateJobReviewBlocked) as caught:call()
        self.assertNotIn('secret source',str(caught.exception))

if __name__=='__main__':unittest.main()
