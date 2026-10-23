"""Fail-closed output-only handoff from DeepSeek Harness to owned repair sessions.

This module NEVER runs the DeepSeek Harness SDK, a shell, model inference,
external code, or a verifier. Its output is a candidate, not an authorization.
"""
from __future__ import annotations

import hashlib
import json
import re

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_TASK_ID = re.compile(r"[0-9a-f]{32}\Z")
MAX_OUTPUT_BYTES = 3_000
MAX_CHANGES = 3
MAX_CHANGE_BYTES = 1_500


class HarnessHandoffRejected(ValueError):
    """Untrusted Harness output or missing owned-task bindings."""


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise HarnessHandoffRejected("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _nonfinite(_):
    raise HarnessHandoffRejected("NONFINITE_JSON")


def _check_prepared_task(task):
    # Only the public dictionary returned by the existing fixed owned
    # CODEX_AGENT repair service is accepted. This is not customer admission.
    if type(task) is not dict or task.get("engine") != "CODEX_AGENT":
        raise HarnessHandoffRejected("OWNED_SESSION_REQUIRED")
    if (task.get("proposal_protocol") != "ast_statement_v1"
            or task.get("approved_file") != "subject.py"):
        raise HarnessHandoffRejected("UNSUPPORTED_OWNED_PROTOCOL")
    if (type(task.get("task_id")) is not str or not _TASK_ID.fullmatch(task["task_id"])
            or type(task.get("case_id")) is not str or not task["case_id"]
            or type(task.get("revision")) is not int or task["revision"] < 0):
        raise HarnessHandoffRejected("INVALID_TASK_IDENTITY")
    for name in ("source_sha256", "tests_sha256"):
        if type(task.get(name)) is not str or not _HEX64.fullmatch(task[name]):
            raise HarnessHandoffRejected("MISSING_OWNED_HASH_BINDING")
    lines = task.get("editable_lines")
    if (type(lines) is not list or not lines or len(lines) > 200
            or any(type(line) is not int or line <= 0 for line in lines)
            or len(set(lines)) != len(lines)):
        raise HarnessHandoffRejected("INVALID_EDITABLE_SCOPE")
    return set(lines)


def prepare_harness_handoff(final_response, owned_task):
    """Convert an SDK result.final_response to an UNADMITTED candidate.

    The caller must obtain owned_task from an already-authorized, live,
    owned-only RepairService.prepare(..., 'CODEX_AGENT') session. This
    function does not check that session is live, and makes no verifier call.
    Only later explicit submission through the existing trusted service may
    verify the candidate in its existing isolated Docker verifier.
    """
    scope = _check_prepared_task(owned_task)
    if type(final_response) is not str:
        raise HarnessHandoffRejected("STRING_OUTPUT_REQUIRED")
    try:
        raw = final_response.encode("utf-8", "strict")
    except UnicodeError:
        raise HarnessHandoffRejected("INVALID_UTF8_OUTPUT") from None
    if not raw or len(raw) > MAX_OUTPUT_BYTES:
        raise HarnessHandoffRejected("OUTPUT_BYTE_LIMIT")
    try:
        proposal = json.loads(final_response, object_pairs_hook=_unique, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, TypeError):
        raise HarnessHandoffRejected("STRUCTURED_JSON_REQUIRED") from None
    if type(proposal) is not dict or set(proposal) != {"changes"}:
        raise HarnessHandoffRejected("PROPOSAL_KEYS_REJECTED")
    changes = proposal["changes"]
    if type(changes) is not list or not (1 <= len(changes) <= MAX_CHANGES):
        raise HarnessHandoffRejected("CHANGE_BUDGET_REJECTED")
    seen = set()
    for change in changes:
        if type(change) is not dict or set(change) != {"line", "new"}:
            raise HarnessHandoffRejected("CHANGE_FORMAT_REJECTED")
        line, new = change["line"], change["new"]
        if type(line) is not int or line not in scope or line in seen:
            raise HarnessHandoffRejected("CHANGE_OUTSIDE_EDITABLE_SCOPE")
        seen.add(line)
        if type(new) is not str or not new or '\x00' in new or '\r' in new:
            raise HarnessHandoffRejected("UNSAFE_REPLACEMENT")
        try:
            length = len(new.encode("utf-8", "strict"))
        except UnicodeError:
            raise HarnessHandoffRejected("UNSAFE_REPLACEMENT") from None
        if length > MAX_CHANGE_BYTES:
            raise HarnessHandoffRejected("UNSAFE_REPLACEMENT")
    canonical = json.dumps(proposal, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False)
    if len(canonical.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise HarnessHandoffRejected("CANONICAL_BYTE_LIMIT")
    return {
        "schema": 1,
        "handoff_kind": "DEEPSEEK_HARNESS_OUTPUT_ONLY",
        "admission": "UNADMITTED_EXTERNAL_CANDIDATE",
        "task_id": owned_task["task_id"],
        "case_id": owned_task["case_id"],
        "revision": owned_task["revision"],
        "source_sha256": owned_task["source_sha256"],
        "tests_sha256": owned_task["tests_sha256"],
        "proposal_json": canonical,
        "proposal_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "model_identity_attested": False,
        "independently_verified": False,
        "customer_execution_authorized": False,
        "delivery_authorized": False,
    }
