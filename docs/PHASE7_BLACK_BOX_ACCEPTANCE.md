# BountyForge Phase 7 Black Box acceptance, 2026-10-22

**Test method:** a separate Python process invokes the installed project
CLIs over their actual stdin, stdout, exit-code and filesystem boundaries.
No special internal-test return values stand in for those interfaces.

The current entry points are:
`python -m scripts.phase7_owned_demo` and
`python -m bountyforge.paid_intake --store <path>`.

## Concrete Black Box finding: synthetic CLI ignores all arguments

**Severity: Medium, operator integrity / misleading command behavior.**

**Observed pre-fix defect:** the original `scripts/phase7_owned_demo.py`
used `main()` without parsing `sys.argv`. It therefore treated
`--execute-customer`, `--payment-verified`, arbitrary customer path
strings and other arguments exactly as the no-argument demo and printed
the same success-shaped `AWAITING_OWNER_APPROVAL` result. Although only
fixed owned program bytes ran, this could mislead an operator into
believing a supplied external operation was accepted.

**Root cause:** the demonstration CLI discarded external arguments before
constructing a fresh synthetic private ledger and replaying fixed source.

**Minimal fix:** refuse *all* CLI arguments with exit status 2 and a
fixed, sanitized stderr message before any temporary state is created.
Never echo raw values that might contain private file paths or secrets.

## Actual process-boundary acceptance scenarios

`tests/test_blackbox_cli_acceptance.py` invokes a real Python subprocess.
No network mock is treated as a verified live Stripe transaction.

1. **Healthy synthetic flow:** strict JSON, expected owned-only
   `AWAITING_OWNER_APPROVAL` state, owner-delivery false, payment false,
   private execution false, model calls zero, temporary files removed.
2. **Unsupported input and authorization claims:** customer source,
   `--execute-customer`, `--payment-verified`, positional data and
   `--help` all rejected before mutation. No sensitive argument echoed.
3. **Deterministic replay:** two separate CLI invocations produce
   identical owned-only receipts and leave no persistent external job.
4. **Unauthorized payment intake:** the real payment-review CLI,
   launched with a simulated fake restricted key and `GITHUB_ACTIONS=true`,
   rejects before contacting Stripe or writing a private database.
5. **Oversized untrusted input:** the payment-review CLI rejects an
   oversized synthetic request before making a provider request or
   creating storage.

**Safety oracle:** zero real customer bytes accepted, zero external code
execution, zero payment transfers, zero provider/model inference,
zero deliverables sent, no raw secret/path output, and no production writes.

The test does not authorize commercial operation and does not simulate a
successful real paid Stripe order. No real account token or customer source
is ever used. A pass is proof only for these five process scenarios on
the particular tested Linux runner, **not** for production host isolation
or commercial readiness.

## Admission verdict

**NOT_ADMITTED.** The current pinned Docker image has verified actual
manifest/config and four layer/diff-id hashes, but its publisher signature,
signed SBOM and complete dependency provenance remain unverified. Private
per-job host admission, explicit real customer rights/model-sharing
consent, current Stripe payment, independently strong repair success,
owner delivery approval and resilient private hosting are still absent.

Preserve production `main`, both draft PRs, the zero-spend restriction,
no local Mac and no external bounty/customer operations.
