# Private source digest gate — October 21, 2026

**Status:** code + offline owned tests only. **Not deployed, not customer intake, not a code-execution admission.**

This addition follows the separately frozen Phase 4 AST-aware statement comparison
(3/4 verified statement repairs versus 2/4 physical-line repairs on four owned
maintenance cases; run [39697530398](https://github.com/Ledgercorp/BountyForge/actions/runs/39697530398)).
It does **not** change the frozen evaluation source, report or model. The
outstanding commercial boundary is privately verifying which exact bytes an
approved scope describes, *before* any hypothetical execution decision.

## Modules, inputs and authorization boundary

- `bountyforge/private_source_inventory.py` exports `inspect_private_source(root, approval_payload)`.
  Its input is an absolute, owner-private **local directory** with exactly one
  approved Python source and `tests/test_regression.py`; no ZIPs, network
  downloads, package installs or third-party code are admitted.
- A second function `inspect_recorded_private_scope(root, review, session,
  token=..., expected_fence=..., now=...)` binds the inspection to the existing
  `PaidScopeReview` trusted instance. It requires a valid signed saved scope,
  the prior payment-review record and a live fenced review lease, then
  rechecks the journal revision after scanning in case of concurrent revocation
  or cancellation. A valid lease is **only review coordination**, not permission
  to execute source.
- Standalone `inspect_private_source` verifies the *shape* of the supplied
  approved scope but **does not cryptographically authenticate** it.
  It is intended only for a caller already in a trusted review context.
  The lease-bound function verifies the actual HMAC from the trusted
  coordinator's configured key, not an arbitrary customer `approved=true` flag.
- No production signer or owner-approval credential was created/configured
  and no owner identity was independently authenticated.

## Non-executing inspection

- Refuses staging inside the public checkout or a relative/unapproved root.
- Traverses all ancestors and nested source/test directories using
  `openat`-style directory descriptors and `O_NOFOLLOW`.
  This prevents opening a replacement symlinked ancestor at a
  path-inspection-to-open race. Refuses unapproved extra files and directories.
- Requires private owner-owned staging directories (0700 or stricter),
  regular files (0600 or stricter), a single link each, a hard 128 KiB
  bound per file, strict UTF-8 and parseable Python syntax.
- Rejects declared non-standard-library and relative dependencies and common
  dynamic import/exec syntax. This is only a *syntactic preflight*: it does
  **not** prove that a stdlib program is safe, that calls are harmless, that
  dependencies are closed or that source lacks indirect dynamic execution.
- Reads source/test bytes by bounded file-descriptor operations,
  checks file identity during each read, independently hashes both and
  uses constant-time comparison against exactly the approved SHA-256 values.
  **Private bytes never enter the returned JSON evidence.**
- Does not call `exec`, `eval`, a test runner, a model, a package manager
  or an HTTP endpoint.
- Returns only limited digest/count metadata and explicit false values:
  `execution_authorized=false`, `delivery_authorized=false`,
  `source_accepted=false`, `rights_verified=false`,
  `model_sharing_verified=false`, `dependency_admitted=false`,
  `private_worker_admitted=false`. Lease-bound output further reports
  `fresh_payment_verified=false` despite its historic payment-review record.

## Red-green hosted evidence

- Initial standalone test revision `813a0f6`: the module was absent.
- `[39701937220](https://github.com/Ledgercorp/BountyForge/actions/runs/39701937220)`:
  first successful hosted gate, **381 total, 373 passed, 8 default rootfs skips**.
- [39702129453](https://github.com/Ledgercorp/BountyForge/actions/runs/39702129453):
  real **red** test captured a symlink swap of an intermediate ancestor
  between lstat and open; the old code erroneously returned success.
- [39702207513](https://github.com/Ledgercorp/BountyForge/actions/runs/39702207513):
  **green**, 382 total, 374 passed, 8 default rootfs skips after replacing
  the root open with component-wise `O_NOFOLLOW`.
- [39702444111](https://github.com/Ledgercorp/BountyForge/actions/runs/39702444111):
  **red** test: the signed, lease-bound inspection API was absent.
- [39702503179](https://github.com/Ledgercorp/BountyForge/actions/runs/39702503179):
  **green**, 388 total, 380 passed, 8 default rootfs skips. Real private
  temporary SQLite journals and fake signed payments were used, not Stripe.

The last added test also exercises **concurrent revocation during byte
inspection** and must pass in the next hosted acceptance. No new model
benchmark was requested; the historical 1/5, owned structural 2/4 and frozen
paired 3/4 versus 2/4 remain independent, unchanged measurements.

## Explicit limits before anything can be commercially admitted

1. The two private source/test SHA checks are a **point-in-time observation**,
   not immutable sealed custody. A later worker must re-open and independently
   verify the exact bytes in a separately admitted, private execution sandbox.
2. The metadata receipt hashes do not prove legal source rights, model-sharing
   consent, customer identity or a legitimate agreement. A trusted owner must
   inspect those documents outside this module.
3. Historical payment-review presence is not a fresh Stripe payment check.
   Cancellation/dispute/revocation can occur after inspection.
4. The generic namespace prototype still lacks independently reviewed
   rootfs provenance admission, dedicated cgroup controllers, syscall/kernel
   hardening, dependency packaging/closure and complete private source recovery.
5. The inspected source has **never** been given to a model or run by this code.
   There is no customer upload endpoint, persistent hosting, service offer,
   queue enrollment, claim, publication, delivery or payment action.

The original private payment-review SQLite tables, synthetic ledger,
dashboard v11, main and both existing draft PRs remain unchanged outside the
isolated feature-branch additions. Additional infrastructure purchases $0,
Mac access none and confirmed received revenue remains $0.
