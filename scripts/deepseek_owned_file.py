"""Explicit owner-side file intake for an isolated Harness final response.

No DeepSeek SDK, subprocess, shell, or model is launched. Any external Harness
process must be independently sandboxed and produce a bounded UTF-8 JSON file.
This command reads that file and can optionally invoke the EXISTING owned-only
BountyForge Docker verifier after an explicit CLI admission flag.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from deepseek_harness_handoff import HarnessHandoffRejected


def read_candidate_file(path: Path) -> str:
    """Read one stable, owner-private, regular, single-link file without following symlinks."""
    if not isinstance(path, Path) or not path.is_absolute():
        raise HarnessHandoffRejected("ABSOLUTE_CANDIDATE_FILE_REQUIRED")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
    except OSError:
        raise HarnessHandoffRejected("CANDIDATE_FILE_UNAVAILABLE") from None
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or before.st_mode & 0o077
                or not 1 <= before.st_size <= 3000):
            raise HarnessHandoffRejected("CANDIDATE_FILE_SCOPE_REJECTED")
        raw = os.read(fd, 3001)
        after = os.fstat(fd)
        if (len(raw) != before.st_size
                or (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns)
                != (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns)):
            raise HarnessHandoffRejected("CANDIDATE_FILE_CHANGED")
        try:
            return raw.decode("utf-8", "strict")
        except UnicodeError:
            raise HarnessHandoffRejected("CANDIDATE_NOT_UTF8") from None
    finally:
        os.close(fd)


def verify_owned_file(case_id: str, candidate_file: Path, *, allow_owned_verification=False):
    """No implied authorization, no customer inputs, no independent accuracy claim."""
    if allow_owned_verification is not True:
        raise HarnessHandoffRejected("EXPLICIT_OWNED_VERIFICATION_REQUIRED")
    if type(case_id) is not str or not case_id or len(case_id) > 64:
        raise HarnessHandoffRejected("OWNED_CASE_REQUIRED")
    candidate = read_candidate_file(candidate_file)
    # Delay trusted verifier imports until the explicit opt-in and input checks.
    from bountyforge.repair_engines import RepairService
    from deepseek_owned_bridge import verify_owned_harness_response

    service = RepairService()
    prepared = service.prepare(case_id, "CODEX_AGENT")
    wrapped = verify_owned_harness_response(
        service, prepared, candidate, allow_owned_verification=True)
    receipt = wrapped["owned_verifier_receipt"]
    return {
        "kind": "DEEPSEEK_HARNESS_OWNER_FILE_HANDOFF",
        "origin": "UNATTESTED_EXTERNAL_OUTPUT_FILE",
        "case_id": prepared["case_id"],
        "candidate_sha256": wrapped["handoff"]["proposal_sha256"],
        "source_sha256": prepared["source_sha256"],
        "tests_sha256": prepared["tests_sha256"],
        "outcome": receipt["outcome"],
        "state": receipt["state"],
        "receipt_sha256": receipt["receipt_sha256"],
        "verified_owned_development": receipt["independently_verified"] is True,
        "independent_evaluation": False,
        "model_identity_attested": False,
        "model_calls_by_this_cli": 0,
        "customer_execution_authorized": False,
        "delivery_authorized": False,
        "commercial_admission": "NOT_ADMITTED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--candidate-file", type=Path, required=True)
    parser.add_argument("--admit-owned-development-verification", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify_owned_file(
            args.case_id, args.candidate_file,
            allow_owned_verification=args.admit_owned_development_verification)
    except HarnessHandoffRejected as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, OSError):
        print("OWNED_VERIFIER_UNAVAILABLE_OR_REJECTED", file=sys.stderr)
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
