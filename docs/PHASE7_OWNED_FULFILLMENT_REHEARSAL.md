# Phase 7 — Owned-only fulfillment rehearsal

Status: **OFFLINE SYNTHETIC ONLY; private jobs NOT_ADMITTED**.

This engineering slice adds `bountyforge/phase7_owned_demo.py`, its
owned-only CLI `scripts/phase7_owned_demo.py` and focused negative tests.
It **does not** replace `paid_scope_review.py`, the private payment ledger,
the Docker isolation runner or the existing private-job admission contract.

## Exact scope and behavior

One hard-coded synthetic job ID and two fixed, byte-identical,
LeftSock-authored Python source snippets are the *only* executable inputs.
The small original arithmetic function fails its intended test vectors.
Its fixed candidate passes four deterministic test vectors when replayed
in-process with empty builtins. No AI generated the repair. No model calls,
external source access, Python package installs or network requests occur.

The demo uses private temporary SQLite storage, full transactions and
revision-fenced state changes:

`CREATED → SCOPE_REVIEWED → PROPOSED → VERIFIED →
AWAITING_OWNER_APPROVAL` with a terminal `HELD` revocation path.

The reviewer package contains only fixed owned-fixture hashes and state
metadata. The strict package digest, owner-only file permissions and exact
file bytes are checked before the final SQLite transition. Duplicate or
stale job claims, premature success, forged payment/consent, modified
package bytes and invalid job IDs are rejected. A finished package is a
private owner-review receipt, **not a deliverable sent to a customer**.

Run safely on Linux:

`python -m unittest tests/test_phase7_owned_demo.py -v`

`python -m scripts.phase7_owned_demo`

## Clear limitations

- The demo creates a **synthetic** scope record, not evidence of real
  customer rights, contract assent or consent to model sharing.
- It deliberately reports `real_payment_verified=false`,
  `delivery_authorized=false` and `private_execution_authorized=false`.
- The fixed owned-code replay tests four trivial vectors, and provides
  **no new benchmark accuracy or commercial repair-success claim**.
- The disposable SQLite database is not a production customer ledger,
  and no durable private hosted volume or backup has been admitted.
- SQLite and a separate filesystem package are not one atomic durability
  transaction across a system crash. Orphan packages fail closed rather
  than conferring delivery authority.
- The owned program is interpreted in-process only because the bytes are
  hardcoded and compared to an exact immutable fixture. It is not a
  sandbox for arbitrary uploaded Python.
- Existing Phase 6 runtime image integrity evidence is preserved.
  Independent publisher signing, provenance attestations and SBOM
  remain unverified; Docker Official Image status is not a signed claim.
- Previous 20/20 owned Docker isolation and all frozen repair scores
  are unchanged.

**Commercial status: NOT_READY. Actual execution: NOT_ADMITTED.
Received revenue: $0.** No customer files, financial transactions, Mac
access, production merge/deploy, paid inference, public posting or
additional infrastructure spend.
