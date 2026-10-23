# Phase 8: owned synthetic orders — NONPRODUCTION

This rehearsal connects a synthetic order to simulated payment review, a fixed
synthetic scope, the existing Phase 7 durable owned job, independent owned repair
verification, and a hashed local review package. Its terminal successful state is
`AWAITING_OWNER_APPROVAL`. It cannot approve, deliver, accept customer source, or
execute customer code. Revenue and model calls remain zero.

**This is an owned provider simulator, not a real Stripe sandbox integration.**
`StripeOrderGate` currently admits only live-shaped checkout IDs and restricted
live key configuration. No Stripe TEST adapter exists in this path; real Stripe
TEST integration remains blocked/unverified. No credentials are requested or
read, and no Stripe API requests occur in this rehearsal.

## Boundaries

- The provider is a real subprocess HTTP server bound to `127.0.0.1` on an
  ephemeral port. The coordinator accepts only its numeric loopback port, three
  fixed resource paths, and one fixed synthetic checkout identifier. No arbitrary
  URL, redirect, proxy, customer identifier, source path, or payment proof input
  is accepted. Response size, request count and socket timeouts are bounded.
- `SimulatorStripeGate` inherits the existing `StripeOrderGate.verify` validation
  with a fixed simulator-only `_get` transport. Fixture `livemode` and `cs_live_`
  fields exist solely to exercise that unchanged validator. They are fake values.
  A fresh random nonce rejects stale response envelopes. This is not authenticated
  provider provenance and does not establish real payment.
- `SyntheticOrder.run` requires the exact simulator gate class. The existing
  `PaidReviewLedger` exact-class admission check rejects it. `PaidScopeReview`,
  `StripeOrderGate`, and production-shaped payment/scope tables are unchanged.
- A dedicated empty, private owner-owned directory must be explicitly initialized.
  Files are private, regular, single-link files; symlinks, FIFOs, unknown workspace
  entries, foreign database tables, and inconsistent journal evidence fail closed.
- The labeled `phase8.SIMULATION_ONLY.sqlite3` database reuses `OwnedOnlyLedger`
  `jobs` and `events`, with separate `simulation_only_identity`,
  `simulation_only_order`, and `simulation_only_evidence` tables. Payment and scope
  records explicitly keep `real_payment_verified` and `owner_consent_verified`
  false. The synthetic scope fixes the owned source/patch hashes and expiry;
  it never proves customer rights or authorizes private execution.
- An advisory file lock serializes cooperating workers. SQLite FULL synchronous
  commits persist each transition. Revision checks and exact event/evidence
  validation fence stale or altered state. Lock release on process death permits
  recovery. A simultaneous hold request receives `worker_busy` and must be retried
  after the active worker exits; there is no asynchronous cancellation service.

## Flow and recovery

Each invocation freshly reads the three simulated provider records. Rejected
payment evidence cannot create an owned job. A valid simulated review is recorded
before scope review; the scope is recorded before the fixed owned job starts.
The owned job then advances through `CREATED`, `SCOPE_REVIEWED`, `PROPOSED`, and
`VERIFIED`. An independent sanitized Python subprocess runs the exact hard-coded
Phase 7 source/repair and four test vectors. No models or customer bytes are used.

Before final packaging, all three payment records are freshly read again and
scope expiry is checked again after those reads. The local review package binds
SHA-256 hashes of payment evidence, synthetic scope, the owned review package and
independent verification report, along with source and patch hashes. Its hash is
committed before the owned job enters `AWAITING_OWNER_APPROVAL`.

Duplicate requests recheck payment, scope, all package bytes and their hashes;
they do not create another job or rerun the independent subprocess. Refunds,
disputes, cancellation, revocation, expired scope, stale response replay and
package tampering block advancement. Explicit holds are terminal. Provider outage
blocks the current attempt but permits retry. Existing review files are historical
artifacts after a hold; they confer no current authorization.

The `--stop-after payment|scope|proposed|verified|packaged` switches support local
restart tests. `--pause-after-scope` emits a checkpoint and pauses ten seconds for
a test to kill the worker. Restart resumes committed state after rechecking current
evidence. The tests exercise a real killed subprocess and all listed checkpoints.
An interrupted partial artifact write fails closed if the existing bytes do not
match exactly; manual review/new rehearsal workspace is needed in that case.
There is no claim of recovery from every possible filesystem or power failure.
Hashes detect inconsistent edits; an owner who can coherently rewrite the entire
private database and all artifacts is outside this rehearsal's integrity boundary.

## Local commands

From the checkout, create a new private directory and initialize it:

```bash
REHEARSAL_ROOT=$(mktemp -d /tmp/bountyforge-phase8.XXXXXX)
python -m scripts.phase8_synthetic_order init --root "$REHEARSAL_ROOT"
python -m scripts.phase8_synthetic_order provider --scenario paid
```

The last command runs in its own terminal and prints its numeric `port`. In another
terminal, use that port and the same `REHEARSAL_ROOT` value:

```bash
printf '%s' '{"session_id":"cs_live_BountyForgeSIMULATIONONLY0001"}' |
  python -m scripts.phase8_synthetic_order run --root "$REHEARSAL_ROOT" --port 12345
python -m scripts.phase8_synthetic_order hold --root "$REHEARSAL_ROOT" --reason revoked
```

Replace `12345` with the printed port. Stop the provider with Ctrl-C when finished.
Use a fresh initialized directory for another rehearsal. Scenarios are `paid`,
`unpaid`, `underpaid`, `cancelled`, `disputed`, `refunded`, `replay`, and
`invalid_session`. No real payment or delivery command exists.

## Verification

```bash
python -m unittest tests.test_phase8_synthetic_order_process tests.test_phase8_synthetic_order_integrity -v
python -m unittest discover -s tests -v
```

The Phase 8 process tests cross real HTTP, subprocess and SQLite boundaries.
They cover duplicates, payment rejection cases, later refund, refund immediately
before final review, outage/retry, response replay, malformed/oversized/redirect/error
responses, expiry including expiry during the final provider read, durable holds,
package/journal tampering, killed-worker recovery, checkpoint recovery, FIFO
rejection, unsupported customer/approval/delivery operations and isolation from
existing paid-review admission. Faulting HTTP fixtures live under `tests/support`.

Verified on 2026-10-23: **21/21 Phase 8 tests passed**. Full repository unittest
suite: **513 tests run, 8 skipped, zero failures**. The eight skips are the
existing `test_isolation.BoundaryTests` cases because the Linux namespace rootfs
is not provisioned; this run does not establish private sandbox acceptance.
A separate local first/duplicate rehearsal observed one owned job, six then three
provider requests, and one then zero independent subprocess replays. Both remained
`AWAITING_OWNER_APPROVAL` with identical package hashes and all real-payment,
owner-consent, private-execution and delivery authorization fields false.
