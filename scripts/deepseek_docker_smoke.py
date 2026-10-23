"""Real, model-free Docker acceptance for the output-only Harness bridge.

Only a hardcoded LeftSock-owned developmental fixture is admitted.
No external source, SDK, provider, API key, or untrusted repository is read.
Run only on an already-authorized Linux Docker host after pulling the
existing digest-pinned verifier image. A passing result proves no repair quality.
"""
from __future__ import annotations

import json

from bountyforge.curated_docker import IMAGE
from bountyforge.repair_engines import RepairService
from deepseek_owned_bridge import verify_owned_harness_response
from deepseek_harness_handoff import HarnessHandoffRejected

CASE_ID = "weighted-mix"
# Known deliberately incorrect change: guaranteed to fail the owned acceptance
# tests under normal conditions. This proves rejection and receipt handling,
# NOT model accuracy or an autonomously generated repair.
SYNTHETIC_SDK_RESPONSE = '{"changes":[{"line":4,"new":"denominator = 123"}]}'


def run():
    # Only the trusted, existing service is instantiated. No model launches.
    service = RepairService()
    task = service.prepare(CASE_ID, "CODEX_AGENT")
    assert task["state"] == "AWAITING_CODEX_CANDIDATE"
    assert task["classification"] == "OWNED_DEVELOPMENT"
    assert task["source_sha256"]
    assert task["tests_sha256"]
    assert task["editable_lines"]
    assert IMAGE.startswith("python@sha256:")

    # Closed by default; no calls to the verifier and no attempt consumed.
    try:
        verify_owned_harness_response(service, task, SYNTHETIC_SDK_RESPONSE)
    except HarnessHandoffRejected as exc:
        assert str(exc) == "EXPLICIT_OWNED_VERIFICATION_REQUIRED"
    else:
        raise AssertionError("Disabled bridge allowed execution")
    assert service._get(task["task_id"], 0, "CODEX_AGENT")["public"]["revision"] == 0

    result = verify_owned_harness_response(
        service, task, SYNTHETIC_SDK_RESPONSE, allow_owned_verification=True)
    receipt = result["owned_verifier_receipt"]
    assert receipt["case_id"] == CASE_ID
    assert receipt["engine"] == "CODEX_AGENT"
    assert receipt["outcome"] == "TEST_FAILED"
    assert receipt["independently_verified"] is False
    assert receipt["targeted"]["passed"] is False
    assert receipt["targeted"]["tests_run"] >= 1
    assert receipt["runtime_admission"]["untrusted_execution_certified"] is False
    assert result["commercial_admission"] == "NOT_ADMITTED"
    assert result["candidate_origin"] == "UNATTESTED_EXTERNAL_HARNESS_OUTPUT"
    assert result["customer_execution_authorized"] is False
    assert result["delivery_authorized"] is False
    assert result["handoff"]["source_sha256"] == task["source_sha256"]
    assert result["handoff"]["tests_sha256"] == task["tests_sha256"]
    assert result["handoff"]["proposal_sha256"]
    assert receipt["receipt_sha256"]

    # A stale session snapshot may never be replayed after a real attempt.
    try:
        verify_owned_harness_response(
            service, task, SYNTHETIC_SDK_RESPONSE, allow_owned_verification=True)
    except HarnessHandoffRejected as exc:
        assert str(exc) == "LIVE_OWNED_SESSION_REQUIRED" or str(exc) == "OWNED_SESSION_IDENTITY_CHANGED"
    else:
        raise AssertionError("Stale task handoff replay was accepted")

    # Separate independently verified POSITIVE path using a hand-authored,
    # public development correction. This is not a model-generated patch, is
    # not unseen evaluation, and does not grant release/customer authority.
    positive = RepairService()
    good_task = positive.prepare(CASE_ID, "CODEX_AGENT")
    manually_authored = '{"changes":[{"line":4,"new":"denominator = sum(weight for _, weight in pairs)"}]}'
    accepted = verify_owned_harness_response(
        positive, good_task, manually_authored, allow_owned_verification=True)
    good_receipt = accepted["owned_verifier_receipt"]
    assert good_receipt["outcome"] == "VERIFIED", good_receipt["outcome"]
    assert good_receipt["state"] == "AWAITING_OWNER_APPROVAL"
    assert good_receipt["independently_verified"] is True
    assert good_receipt["targeted"]["passed"] is True
    assert good_receipt["independent"]["passed"] is True
    assert good_receipt["targeted"]["tests_run"] >= 1
    assert good_receipt["independent"]["tests_run"] >= 1
    assert good_receipt["delivery_authorized"] is False
    assert good_receipt["customer_execution_authorized"] is False
    assert accepted["commercial_admission"] == "NOT_ADMITTED"
    assert accepted["candidate_origin"] == "UNATTESTED_EXTERNAL_HARNESS_OUTPUT"

    return {
        "kind": "DEEPSEEK_HARNESS_BRIDGE_REAL_DOCKER_REJECTION_SMOKE",
        "classification": "OWNED_DEVELOPMENT",
        "origin": "HARDCODED_SYNTHETIC_CANDIDATE_NOT_MODEL_OUTPUT",
        "case_id": CASE_ID,
        "sandbox": receipt["targeted"]["sandbox"],
        "outcome": receipt["outcome"],
        "verified_repairs_from_model": 0,
        "manually_authored_owned_verified": True,
        "manual_candidate_receipt_sha256": good_receipt["receipt_sha256"],
        "manual_targeted_tests_run": good_receipt["targeted"]["tests_run"],
        "manual_independent_tests_run": good_receipt["independent"]["tests_run"],
        "targeted_tests_run": receipt["targeted"]["tests_run"],
        "receipt_sha256": receipt["receipt_sha256"],
        "source_sha256": task["source_sha256"],
        "tests_sha256": task["tests_sha256"],
        "default_engine_changed": False,
        "customer_execution_authorized": False,
        "commercial_admission": "NOT_ADMITTED",
        "model_calls": 0,
        "additional_spending_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
