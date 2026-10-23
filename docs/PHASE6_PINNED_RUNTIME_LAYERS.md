# Phase 6 runtime image layer custody, 2026-10-22 UTC

**Scope:** anonymous public Docker Official Python image, fixed SHA-256
manifest, Linux/AMD64. Read-only, no customer source and no execution.

## Exact pinned reference and code fix

BountyForge's digest `sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590`
identifies a **single-platform Docker manifest**, not a multi-platform
OCI index. The Phase 5 index-only verifier was corrected to recognize
both valid reference types without relaxing digest checks.

Docker Hub identifies the image as historical Python 3.11.17 Slim
Bookworm. This public catalog identity is not a verified image signature.
https://hub.docker.com/layers/library/python/3.11.17-slim-bookworm/images/sha256-8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590

## Actual public blob verification

The anonymous registry client used only fixed official hosts and
static digest URLs, with no mutable tags or bearer propagation to CDN.
Its authorization request used the publicly scoped Docker Hub token
service. Its registry path was strictly `library/python`.

Registry CDN URLs initially failed by design. A sanitized probe
identified `production.cloudfront.docker.com`, which Docker's official
network allowlist and May 2026 release notes independently identify as
their supported image CDN. This precise HTTPS hostname was allowlisted
while the token-stripping, digest-path checks, no-host wildcard and
single-redirect restrictions remained in place:
https://docs.docker.com/desktop/enterprise/allow-list/
https://docs.docker.com/docker-hub/release-notes/

**Verified metadata run:**
https://github.com/Ledgercorp/BountyForge/actions/runs/39765769522

- Image manifest SHA-256 matched the fixed BountyForge digest.
- Actual image configuration SHA-256 independently matched
  `sha256:141fe9b385f3bb6d618c07ace1836c0b3c72bf525566ac3eb13cd1f405069877`.
- The manifest identified exactly four gzip-compressed layers.
- No source code, Docker images or credentials were published.

**Verified all-layer run:**
https://github.com/Ledgercorp/BountyForge/actions/runs/39766309534

- Four of four compressed layer SHA-256 hashes matched the manifest.
- Four of four uncompressed gzip DiffIDs matched the configuration.
- Compressed bytes verified: **49,907,229**.
- Uncompressed bytes verified: **142,461,952**.
- Full hosted tests: **476 total, 468 passed, eight existing Linux
  namespace/rootfs skips, zero failures**.
- GitHub artifact: `12420416425`, ZIP SHA-256
  `d7997dd15a1058e19fbe37fd71bb275f0c8e82ca0b2b67758974857d694f7e2f`.
- No extracted tar archives, package installs, model calls, customer
  code execution, customer payment or transfers occurred.

The new `bountyforge/oci_layer_digest.py` reads compressed blobs
incrementally, imposes compressed and uncompressed size limits,
calculates both hashes, rejects unexpected archives/trailing bytes,
and never extracts or executes tar contents. Its bounded offline tests
cover truncation, corruption, wrong DiffIDs, malformed descriptors,
expansion bombs and I/O failure.

The one-shot public layer-probe step was **removed from automatic PR
checks immediately after success**. The inspection code remains
available for an authorized recheck. No recurring network or Docker
pull was scheduled.

## Still NOT_ADMITTED

The exact image contents are now cryptographically *integrity*
verified against BountyForge's own policy digest. That does not
authenticate the original publisher or build process.

- No independently verified trusted publisher signature, builder
  identity or authenticated upstream source-to-image relationship.
- No cryptographically verified software bill of materials or
  complete reproducible build/distro dependency chain.
- No independent security review of this historical image's known
  vulnerabilities. A digest pin prevents substitution, not CVEs.
- No production private job host, controlled I/O policy, kernel/ABI
  threat-model acceptance or fresh per-job provenance handshake.
- No actual consent from a real customer, source-sharing permission,
  fresh paid order or verified commercial repair result.
- No execution or delivery capability is issued by the new code.

Existing 20/20 controlled Docker negative security probes remain
valid only for owned fixtures. The new results do not authorize
untrusted code. Do not automatically upgrade/change the pinned image.

**Overall status: NOT_ADMITTED, NOT_READY, verified revenue $0,
additional spending $0.** Main, both PRs, dashboard and frozen
benchmarks are preserved. No Mac used.
