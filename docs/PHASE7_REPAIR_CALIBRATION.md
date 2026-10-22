# Phase 7 — Owned repair calibration catalog

**Status:** Four LeftSock-authored maintenance defects, no model scoring.

New `bountyforge/phase7_calibration.py` contains four distinct, public
calibration problems and their reference fixes:

1. Pagination boundary, first-item displacement.
2. Tenant-scoping collision in an identifier lookup.
3. Backoff delay milliseconds/seconds unit mismatch.
4. Even-length median handling and multiline correction.

Each case has multiple deterministic vectors, a named target function,
unchanged original program and a reference patch. `manifest()`
fingerprints each original/reference source and the ordered catalog.
`replay_catalog()` independently executes only the exact authored
source and reference bytes with a restricted builtin mapping,
demonstrating that each original fails at least one vector and each
reference passes all of them.

This proves that the *owned evaluator fixtures* are internally coherent.
It **does not** prove that GPT-OSS can produce the fixes, improve its
accuracy or generalize to external software. Reference patches appear
in this repository, so these fixtures are publicly exposed and
must not be scored as an unseen held-out commercial benchmark.

No Groq calls, provider credentials, new inference expense, other-party
software, network access or payment processing occurred. The historical
frozen evaluation scores are preserved.

Related independently tested owned fulfillment:
`docs/PHASE7_OWNED_FULFILLMENT_REHEARSAL.md`.

**Readiness: NOT_ADMITTED, paid fulfillment NOT_READY.**
Publisher signatures, signed SBOM, complete execution admission, rights
and model-sharing consent, fresh paid order and representative real
repair accuracy still remain unverified.
