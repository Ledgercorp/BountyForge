"""Sanitized owned-fixture Docker evidence only. Never customer-code admission."""
from __future__ import annotations
import re
from bountyforge.curated_docker import IMAGE

CONTROLS = frozenset(('network_denied','loopback_inference_unreachable',
 'source_writes_denied','root_writes_denied','secrets_absent','uid_unprivileged',
 'capabilities_empty','no_new_privileges','seccomp_active',
 'memory_limit_enforced','swap_disabled','cpu_quota_verified',
 'pid_limit_verified','tmpfs_bounded_noexec','wall_clock_enforced',
 'cleanup_verified','output_bounded','docker_socket_absent',
 'pid_pressure_enforced','cpu_pressure_enforced'))
INT_BOUNDS = {'pid_current_at_denial':(1,64),'pid_denial_events':(1,100000),
              'probe_threads':(1,80),'cpu_throttled_periods':(1,100000)}
FLOAT_BOUNDS = {'cpu_pressure_wall_seconds':(0,20),
                'cpu_pressure_used_seconds':(0,25)}

class OwnedBoundaryRejected(ValueError):
    """Incomplete owned-only sandbox evidence."""

def review_owned_docker_proof(raw):
    """Strictly review existing trusted probe output, not provenance or rights."""
    if not isinstance(raw,dict):
        raise OwnedBoundaryRejected('Owned Docker observations missing')
    if any(raw.get(k) is not True for k in CONTROLS):
        raise OwnedBoundaryRejected('Owned Docker security control missing')
    if raw.get('untrusted_execution_certified') is not False:
        raise OwnedBoundaryRejected('Unexpected customer-execution certification')
    image=raw.get('image_digest')
    if not isinstance(image,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',image):
        raise OwnedBoundaryRejected('Pinned image digest missing')
    if image != IMAGE.split('@',1)[1]:
        raise OwnedBoundaryRejected('Owned Docker image digest mismatch')
    for field,(low,high) in INT_BOUNDS.items():
        value=raw.get(field)
        if type(value) is not int or not low<=value<=high:
            raise OwnedBoundaryRejected('Invalid owned limit-pressure counts')
    for field,(low,high) in FLOAT_BOUNDS.items():
        value=raw.get(field)
        if type(value) not in (float,int) or not low<value<=high:
            raise OwnedBoundaryRejected('Invalid owned resource-pressure values')
    if raw['cpu_pressure_used_seconds'] > raw['cpu_pressure_wall_seconds']*1.15+0.2:
        raise OwnedBoundaryRejected('Reported CPU usage exceeds pinned bound')
    # Never copy raw output, paths, cgroup addresses or provider response fields.
    return {'schema':1,'kind':'owned_docker_enforcement_review',
        'controlled_owned_fixture_observed':True,'control_count':len(CONTROLS),
        'docker_image_digest':image,'observed_pid_ceiling':64,
        'observed_memory_bytes':268435456,'observed_cpu_quota':'1cpu',
        'network_denied':True,'write_and_privilege_denied':True,
        'owned_resource_pressure_verified':True,
        'independent_image_producer_identity_verified':False,
        'separate_rootfs_tree_attested':False,'private_custody_authorized':False,
        'private_execution_admitted':False,'customer_source_authorized':False,
        'model_sharing_authorized':False,'fresh_payment_verified':False,
        'production_delivery_authorized':False}

def compare_review_only_custody(boundary,custody):
    """Metadata comparison; even forged positives cannot grant execution."""
    if not isinstance(boundary,dict) or boundary.get('kind')!='owned_docker_enforcement_review':
        raise OwnedBoundaryRejected('Owned Docker review missing')
    if not isinstance(custody,dict):
        raise OwnedBoundaryRejected('Private custody evidence missing')
    if any(not isinstance(custody.get(k),str) or
           not re.fullmatch(r'[0-9a-f]{64}',custody[k])
           for k in ('source_sha256','tests_sha256')):
        raise OwnedBoundaryRejected('Custody digest metadata invalid')
    observed=(custody.get('kind')=='private_custody_snapshot_verified'
              and custody.get('signed_scope_matched') is True
              and custody.get('review_lease_validated') is True
              and custody.get('hashes_verified') is True
              and boundary.get('controlled_owned_fixture_observed') is True)
    return {'schema':1,'kind':'owned_container_private_custody_review_matrix',
      'owned_docker_observed':boundary.get('controlled_owned_fixture_observed') is True,
      'private_custody_metadata_present':observed,
      'live_customer_source_executed':False,
      'private_custody_reopened_in_container':False,
      'rootfs_producer_identity_verified':False,
      'customer_rights_verified':False,'fresh_payment_verified':False,
      'dependency_closure_verified':False,'private_execution_admitted':False,
      'production_delivery_authorized':False,'not_ready':True}


def review_signed_snapshot_with_owned_probe(snapshot_root, review, session, *,
                                            token, expected_fence, now, owned_proof):
    """Reopen signed current custody and compare owned Docker *metadata* only.

    No snapshot is mounted in Docker, no private code is executed or shared,
    and no caller-supplied proof can create customer execution permission.
    """
    proof = review_owned_docker_proof(owned_proof)
    from bountyforge.private_source_custody import verify_recorded_private_snapshot
    custody = verify_recorded_private_snapshot(
        snapshot_root, review, session, token=token,
        expected_fence=expected_fence, now=now)
    return compare_review_only_custody(proof, custody)
