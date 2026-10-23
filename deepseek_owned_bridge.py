"""Trusted, explicit, owned-only verifier bridge. Never launches DeepSeek.

The untrusted Harness process MUST run separately, with no reference to the
trusted RepairService object, credentials, or executable tools. This bridge
consumes only its final response string; it does not admit an SDK process.
"""
from __future__ import annotations

from deepseek_harness_handoff import HarnessHandoffRejected, prepare_harness_handoff

_BINDINGS = (
    'task_id', 'case_id', 'revision', 'source_sha256', 'tests_sha256',
    'source', 'approved_file', 'editable_lines', 'proposal_protocol',
    'classification', 'independent_evaluation', 'state', 'max_attempts',
    'customer_execution_authorized', 'delivery_authorized',
)


def verify_owned_harness_response(service, prepared_task, final_response, *, allow_owned_verification=False):
    """Submit one bounded external candidate to the existing trusted verifier.

    Only a trusted owner-side process may call this function. The `service`
    must be the exact existing RepairService instance holding a live,
    capability-fenced CODEX_AGENT owned session. The explicit flag is a
    developer switch, NOT commercial permission or sandbox admission.
    """
    if allow_owned_verification is not True:
        raise HarnessHandoffRejected('EXPLICIT_OWNED_VERIFICATION_REQUIRED')
    # Lazy import: importing this module or parsing a handoff does not spin up
    # the verifier, Docker, an inference engine, an SDK, or any network client.
    from bountyforge.repair_engines import RepairService, RepairRejected

    if type(service) is not RepairService:
        raise HarnessHandoffRejected('TRUSTED_REPAIR_SERVICE_REQUIRED')
    handoff = prepare_harness_handoff(final_response, prepared_task)
    try:
        live_task = service._get(handoff['task_id'], handoff['revision'], 'CODEX_AGENT')['public']
    except (RepairRejected, KeyError, TypeError):
        raise HarnessHandoffRejected('LIVE_OWNED_SESSION_REQUIRED') from None
    if type(live_task) is not dict or any(live_task.get(key) != prepared_task.get(key) for key in _BINDINGS):
        raise HarnessHandoffRejected('OWNED_SESSION_IDENTITY_CHANGED')
    # Verify the authoritative live snapshot as well as the input snapshot.
    canonical = prepare_harness_handoff(final_response, live_task)
    if canonical != handoff:
        raise HarnessHandoffRejected('OWNED_SESSION_IDENTITY_CHANGED')
    receipt = service.submit(handoff['task_id'], handoff['revision'], handoff['proposal_json'])
    return {
        'kind': 'DEEPSEEK_HARNESS_OWNED_VERIFIER_BRIDGE',
        'candidate_origin': 'UNATTESTED_EXTERNAL_HARNESS_OUTPUT',
        'handoff': handoff,
        'owned_verifier_receipt': receipt,
        'independently_verified_owned_development': receipt.get('independently_verified') is True,
        'independent_evaluation': False,
        'customer_execution_authorized': False,
        'delivery_authorized': False,
        'commercial_admission': 'NOT_ADMITTED',
    }
