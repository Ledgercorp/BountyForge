# BountyForge Phase 5C — Review-only private job prerequisites

Status: **REVIEWED_NOT_ADMITTED or blocked**. There is no live private execution.

Module `bountyforge/private_job_contract.py` introduces
`review_private_job_prerequisites(...)`. It does not accept a caller's
`approved=true` flag, a synthetic business invoice or an arbitrary
self-declared trusted image digest as execution evidence.

The function calls the existing actual
`verify_recorded_private_snapshot` for current signed scope, fenced lease
and on-disk snapshot hashes; the owned Docker evidence validator for the
fixed digest; and the new OCI metadata-chain verifier with the **exact**
`IMAGE` pin in `bountyforge.curated_docker`. It then **reopens the
signed custody again** and rejects changed digests or lease fencing.

On review success, it returns a deliberately inert record with:

- `status=REVIEWED_NOT_ADMITTED`
- A non-sensitive snapshot digest and OCI index digest only.
- Seven named unresolved prerequisites.
- `execution_authorized=false`, `delivery_authorized=false`,
  `customer_source_authorized=false` and
  `fresh_payment_verified=false` in every successful return.

Malformed metadata, an invalid actual source lease or changed snapshot,
an unsigned/fake OCI document, a changed image digest or a mismatch
between custody checks cause a sanitized blocked exception. No private
path, token, raw source or provider error reaches that error message.

The implementation is **not** a cryptographic execution ticket,
not a signature-validation service and not a general customer consent
validator. The Docker observation itself remains unsigned and may be
stale, even if its values match the controlled owned-fixture test.
Two custody checks can still become stale immediately after return.
The only safe interpretation of this record is readiness **for further
owner review**, not a grant to run code.

Six local test cases passed before the GitHub push, using isolated
mock verifier boundaries and adversarial input. No real customer
source, Stripe key, model request or arbitrary code was used.

## Outstanding independent evidence

1. Actual OCI index/manifest/config acquisition for BountyForge's
   exact existing Python image and authenticated publisher provenance.
2. Verified compressed layers, SBOM and dependency closure.
3. Dedicated per-job host/kernel/seccomp admission, revalidation
   immediately at the security boundary and safe teardown.
4. Real customer source rights and explicit model-sharing consent.
5. Fresh payment status and owner-approved work and delivery terms.
6. Independent, reliable real-world repair performance and valid
   commercial order management.

Current status **NOT_READY**; revenue $0. Both draft PRs and main
remain untouched outside this feature-branch development. No new
infrastructure charges, Mac work, GPU pods, customer outreach,
customer-code execution or paid inference.
