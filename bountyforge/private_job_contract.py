"""Review future private jobs without creating an execution authority.

All evidence comes from separately invoked verifiers, never caller-owned flags.
Even passing all *reviewable* prerequisites leaves the job NOT_ADMITTED.
"""
from __future__ import annotations

from .oci_runtime_provenance import OCIReviewRejected, verify_pinned_image_reference


class PrivateJobReviewBlocked(ValueError):
    """A current review prerequisite failed. Never include raw evidence."""


BLOCKERS = (
    'publisher_identity_and_attestation_unverified',
    'compressed_layer_content_unverified',
    'signed_sbom_and_dependency_closure_unverified',
    'private_host_per_job_isolation_unverified',
    'customer_rights_and_model_sharing_not_admitted',
    'fresh_payment_not_verified',
    'owner_execution_and_delivery_not_authorized',
)


def review_private_job_prerequisites(snapshot_root, coordinator, session, *,
                                     token, expected_fence, now,
                                     owned_docker_proof, oci_index,
                                     oci_manifest, oci_config):
    """Revalidate current custody twice and check fixed OCI/Docker digests.

    The returned report can NEVER be consumed as an execution capability.
    It does not validate identity or consent documents, customer code or keys.
    """
    from .curated_docker import IMAGE
    from .private_source_custody import (
        PrivateSourceRejected, verify_recorded_private_snapshot)
    from .private_boundary_review import (
        OwnedBoundaryRejected, review_owned_docker_proof)

    def current_custody():
        return verify_recorded_private_snapshot(
            snapshot_root, coordinator, session, token=token,
            expected_fence=expected_fence, now=now)

    try:
        first = current_custody()
        boundary = review_owned_docker_proof(owned_docker_proof)
        if boundary.get('docker_image_digest') != IMAGE.split('@', 1)[1]:
            raise PrivateJobReviewBlocked('Selected container digest mismatch')
        provenance = verify_pinned_image_reference(
            oci_index, oci_manifest, oci_config,
            expected_reference_digest=IMAGE.split('@', 1)[1])
        second = current_custody()
        if provenance.get('pinned_reference_digest') != IMAGE.split('@', 1)[1]:
            raise PrivateJobReviewBlocked('Unexpected index pin')
        if (first.get('snapshot_sha256') != second.get('snapshot_sha256')
                or first.get('lease_fence') != second.get('lease_fence')
                or first.get('source_sha256') != second.get('source_sha256')
                or first.get('tests_sha256') != second.get('tests_sha256')):
            raise PrivateJobReviewBlocked('Private custody changed during review')
        if (first.get('signed_scope_matched') is not True or
                first.get('review_lease_validated') is not True or
                first.get('hashes_verified') is not True):
            raise PrivateJobReviewBlocked('Current signed custody unavailable')
        if (provenance['publisher_signature_verified'] is not False
                or provenance['runtime_execution_admitted'] is not False):
            raise PrivateJobReviewBlocked('Unexpected provenance authorization')
    except (PrivateSourceRejected, OwnedBoundaryRejected, OCIReviewRejected,
            PrivateJobReviewBlocked, ValueError, TypeError, AttributeError,
            KeyError, OSError, OverflowError):
        raise PrivateJobReviewBlocked('Private execution prerequisite review blocked') from None
    # This report does not contain token, session, source path or source bytes.
    return {
        'schema': 1, 'kind': 'private_job_prerequisite_review',
        'status': 'REVIEWED_NOT_ADMITTED',
        'snapshot_sha256': second['snapshot_sha256'],
        'pinned_reference_digest': provenance['pinned_reference_digest'],
        'pinned_reference_kind': provenance['pinned_reference_kind'],
        'owned_container_digest_matched': True,
        'current_signed_custody_reverified': True,
        'oci_pinned_reference_to_config_digests_verified': True,
        'trusted_producer_signature_verified': False,
        'owned_docker_attestation_authenticated': False,
        'private_code_executed': False,
        'source_shared_with_model': False,
        'fresh_payment_verified': False,
        'customer_source_authorized': False,
        'execution_authorized': False,
        'delivery_authorized': False,
        'blocking_requirements': list(BLOCKERS),
    }
