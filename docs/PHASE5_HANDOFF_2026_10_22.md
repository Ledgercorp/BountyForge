# BountyForge Phase 5 — verified engineering handoff (2026-10-22)

## Progress completed

Continued the existing `engineering/revenue-linux-scout-20261021` branch and
preserved both draft PRs, production `main`, frozen repair benchmarks,
dashboard and private customer-execution ban.

**Phase 5A**: `bountyforge/oci_runtime_provenance.py` is a strict, bounded
offline OCI/Docker metadata verifier. It hashes an externally pinned index,
the one Linux/AMD64 child manifest and config, checks layer descriptor
shapes and uncompressed diff-id counts, and rejects malformed media types,
duplicate JSON keys, extra blob URLs, wrong platforms, byte tampering and
ambiguous manifests. It does not download, decompress or execute any layer.

**Phase 5C**: `bountyforge/private_job_contract.py` is a review-only
prerequisite chain. It invokes the *existing signed private source-custody
verifier*, the *existing pinned owned Docker proof review* and the OCI
metadata verifier with the exact `curated_docker.IMAGE` digest. Signed
custody is rechecked at the end, and the resulting decision always remains
`REVIEWED_NOT_ADMITTED` or raises a sanitized blocked exception.

This is not a new execution API, private intake service or customer order.
The container probe result is an unsigned dictionary, so its claimed values
cannot establish a fresh authenticated job boundary. The OCI data itself
is not a publisher signature or signed SBOM.

## Test evidence and scope

Seventeen focused standalone tests passed on isolated Linux before the
final commit. They include mismatched OCI hashes, malformed media types,
wrong platform, duplicate descriptors, apparent approvals, changes to the
signed custody snapshot and inconsistent Docker digests.

The previous two integrated hosted CI runs passed:
- Phase 5A: https://github.com/Ledgercorp/BountyForge/actions/runs/39761657839
  (445 run, 437 passed, 8 existing namespace-rootfs skips).
- Phase 5C: https://github.com/Ledgercorp/BountyForge/actions/runs/39762097354
  (451 run, 443 passed, 8 existing namespace-rootfs skips).

The last additional security-hardening commit adds two negative tests.
Its own GitHub CI run must be checked separately before asserting green.

No real private customer code, Groq calls, paid inference, GPU pods,
public service launch, Docker image pull, Mac access, contract, customer
communication, payment action or repository merge occurred.

## What Phase 5 does *not* prove

1. Actual OCI blobs for the pinned Python image have not been independently
   acquired or authenticated. Complete compressed layer bytes, upstream
   publisher signature, build attestations, SBOM and full dependency closure
   remain unverified. Docker documents the general OCI provenance format:
   https://docs.docker.com/build/metadata/attestations/
2. Existing owned-fixture 20/20 Docker security acceptance applies only to
   those controlled canary commands, not an admitted private customer job.
   Kernel/seccomp review, trusted private storage and isolated per-job
   I/O/security policy remain incomplete.
3. Owner/customer authority to share source with GPT-OSS, fresh paid-order
   verification, live repair reliability and owner-approved delivery are not
   established.
4. The signed scope/lease may be revoked after any review. A review result
   is not a transferable execution ticket. Production fulfillment stays off.
5. Historical model benchmarking remains unchanged: 1/5 historical GPT-OSS,
   2/4 owned structural, 2/4 original line and 3/4 AST statement editor
   on exposed owned fixtures. No live inference or new independent benchmark.

Next authorized engineering path: independently retrieve **actual**
image manifest/config and appropriate signed provenance via a trusted
read-only Linux transport, verify layer bytes and signature trust, then
investigate a dedicated private host with per-job I/O, syscall/kernel,
identity and provenance controls. None is presently admitted.

**Business disposition: NOT_READY. Verified received revenue: $0.**
