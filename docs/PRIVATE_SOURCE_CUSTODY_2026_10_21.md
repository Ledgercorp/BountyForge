# BountyForge private custody snapshot — engineering continuation

Date: October 21/22, 2026 UTC. Status: **offline, owned-only, NOT deployed**.

## Why this exists

The previous read-only signed scope gate verified private source/test hashes at
a particular moment. A later worker still could have reopened different mutable
bytes. This slice introduces a bounded local **copy-and-reverify** mechanism.
It is not private code execution, customer intake, deployment or proof that
reviewed source may be sent to any model.

New modules:
- `bountyforge/private_source_custody.py`
- `tests/test_private_source_custody.py`

## Snapshot capture

`create_review_snapshot(source_root, vault_root, review, session,
token=..., expected_fence=..., now=...)` requires:

- Existing `PaidScopeReview` using private `SQLiteScopeReviewStore` and
  `SQLitePaidReviewStore`, a valid owner-key HMAC-signed source/test scope,
  a valid fenced review lease, no blocking holds and a recorded **historical**
  payment review. The contract does **not** verify actual customer identity,
  consent, model-sharing permission, or a **fresh** Stripe payment.
- Two exactly approved owned/private Python files already on that machine,
  with source SHA-256 and test SHA-256 matching the signed scope.
- A distinct, already present private local vault directory, outside the
  public Git checkout and disjoint from the source tree. No automatic
  provisioning, uploads, secrets or permanent volumes are configured.

The routine rechecks the current staged bytes, opens the separate vault through
no-follow directory descriptors, writes only the verified bytes and a
non-authorizing receipt with owner-only permissions, fsyncs and switches a
random `.pending-<32hex>` name to `sealed-<32hex>` after repeating source
and review checks. It returns only digest/count metadata, not private source.

The prefix **sealed-** means *finished writing the review copy*, **not**
cryptographic sealing, immutability, filesystem read-only enforcement or an
execution admission token. The owner of the private vault could still modify
the files; the verifier detects such modification against the independently
trusted scope hashes. A crash or injected write failure can leave a
non-admitted `.pending-*` directory requiring private cleanup. The test vault
is ephemeral and is not a durability, backup or crash-recovery certification.

## Reverification

`verify_private_snapshot(snapshot_root, approved_payload)` independently
reopens exactly the two files plus `snapshot.json`, rejects extras, type and
permissions changes, symlinks, hardlinks, changed bytes and altered receipt
metadata, then rehashes all content. It does not verify that its **caller**
authenticated `approved_payload`, so it must not be considered an approval
API when directly exposed to untrusted callers.

`verify_recorded_private_snapshot(snapshot_root, review, session,
token=..., expected_fence=..., now=...)` additionally validates the saved
signed scope, review lease, historic payment-record presence and stable
SQLite revision identifiers before and after reopening the snapshot. This
works after the *original* source path has disappeared. Concurrent revocation
or changed payment-review state causes a rejection.

Both verification functions return **no execution, source-acceptance, sharing,
delivery or fresh-payment authorization**. No function in this module invokes
a Python interpreter on customer code, calls external APIs, logs source, edits
existing source or dispatches an autonomous agent.

## Verification

The implementation was developed against new offline tests that exercise:

- Exact byte copies and independent digest-only reopening.
- Origin modified after snapshot without changing the verified copy.
- Snapshot byte/receipt tampering, unexpected files, linked files and
  modified permissions.
- Rejected expired or revoked review leases, invalid signing key, wrong
  fencing token and scope changes.
- Review-state revocation during copy or snapshot reopening.
- Failed partial write and stale payment-review revision.

Github-hosted Linux test evidence:

- [39703791633](https://github.com/Ledgercorp/BountyForge/actions/runs/39703791633):
  red, snapshot module missing.
- [39703996014](https://github.com/Ledgercorp/BountyForge/actions/runs/39703996014):
  first implementation, test schema naming mismatch (`tests_sha256`).
- [39704078809](https://github.com/Ledgercorp/BountyForge/actions/runs/39704078809):
  green, 397 total, 389 passed, eight existing namespace/rootfs skips.
- [39704220082](https://github.com/Ledgercorp/BountyForge/actions/runs/39704220082):
  red, signed later-reverification method not yet defined.
- [39704271773](https://github.com/Ledgercorp/BountyForge/actions/runs/39704271773):
  green, 401 total, 393 passed, eight existing rootfs skips.

The additional final write-failure and payment-revision negatives were added
separately and require confirming their final hosted CI run before counting
them as passed. No live Groq inference was used; the frozen historical 1/5,
owned structural 2/4 and fresh owned paired line 2/4 vs statement 3/4
benchmarks are unchanged.

## Remaining blocked gates

- No production-backed private vault, admitted hosting, backups or recovery.
- No rootfs provenance/sealing, per-job cgroups, dependency closure,
  complete syscall/ABI or kernel containment review.
- No customer-rights, ownership, consent or model-sharing confirmation.
- No execution from snapshots, no private source sent to GPT-OSS, no
  independent real-world repair-quality acceptance.
- No real current Stripe paid order, approved public offer, contracts,
  customer communication, job delivery or transfer of funds.
- A later authorized worker must reopen and reverify bytes and
  signed/fenced scope and separately establish all execution gates.
  Snapshot verification is not a permanent capability. An owner can revoke
  at any time, and verification can become stale immediately afterward.
- The default GitHub-hosted Linux regression still skips eight namespace
  rootfs cases; prior Codex Cloud acceptance passed the eight tests on a
  different Linux kernel and policy. This continuation did not re-run
  namespace or rootfs tests with a real sandbox.

**Preserved:** Main, both draft PRs, dashboard v11, public synthetic durable
ledger, and all frozen benchmark evidence. No new infrastructure purchases,
Mac access, additional inference, external code submissions or revenue.
