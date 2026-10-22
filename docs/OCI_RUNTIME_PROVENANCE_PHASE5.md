# BountyForge Phase 5A — OCI runtime descriptor review

Status: **offline only, NOT_ADMITTED for private customer execution**.

## Scope

`bountyforge/oci_runtime_provenance.py` validates supplied OCI/Docker
**metadata bytes** with an externally expected index SHA-256:

1. A bounded, strict OCI/Docker index JSON with no duplicate keys.
2. Exactly one Linux/AMD64 child manifest descriptor.
3. That manifest's exact advertised size and SHA-256.
4. A referenced image config's exact size and SHA-256.
5. Linux/AMD64 config and a bounded matching count of uncompressed
   `rootfs.diff_ids` and compressed layer descriptors.
6. Rejection of malformed digests, duplicate layer descriptors,
   duplicate platform selectors, unfamiliar metadata, off-registry blob
   URLs, excessive object sizes and missing or mutated fields.

The verifier never retrieves images, extracts archives, executes binaries
or sees customer source code. Returned evidence contains only fixed
field names, digests and counts.

### Trust boundaries

**This is a descriptor-chain check, NOT runtime provenance admission.**

- Input bytes are caller supplied and must be obtained through an
  independently trusted acquisition channel.
- The expected index digest must be pinned independently in trusted
  policy. A claimant supplying both bytes and its own expected hash is
  not authenticating the image.
- Individual compressed layer content is **not supplied or hashed**.
- No upstream publisher signature, provenance attestation, SBOM signature,
  upstream source commit or builder identity is independently verified.
- The OCI manifest's layer IDs and config diff IDs are *claims*, not
  executable content closure.
- Even a complete signature chain would not by itself prove syscall,
  kernel/ABI or customer-code isolation is safe.
- The existing `rootfs_provenance.py` remains a separate bounded
  host-rootfs file inventory, not an OCI image provenance verifier.
- No new runtime or Docker image has been admitted in this phase.

The return object explicitly reports false for compressed-layer-byte
verification, publisher signature, provenance/SBOM, independent pin
origin, execution and delivery authorization.

### Owned-only test evidence

Nine local Linux unit tests passed before GitHub push. Tests exercise a
synthetic OCI document chain, byte tampering, wrong index hash, duplicate
JSON keys, wrong CPU architecture, repeated platform entries, forbidden
external layer URLs, duplicate layer IDs, malformed size/type and absent
uncompressed diff IDs. Synthetic documents are not evidence of
authenticity for the production pinned Python Docker image.

The code is designed for future read-only acquisition of **actual**
index/manifest/config blobs for BountyForge's pinned Docker image, with
cryptographically verified acquisition and publisher attestations treated
as additional independent prerequisites, not implied successes.

### Zero-cost future verification path

Docker documents build attestations as OCI-index-linked provenance and
SBOM records, but attachment and signature policies vary. For this
specific Python Official Image, retrieve and independently verify the
actual manifest and provenance records before asserting any producer
identity. Useful documentation:

- https://docs.docker.com/build/metadata/attestations/
- https://docs.docker.com/build/metadata/attestations/slsa-provenance
- https://docs.docker.com/build/policies/

No purchased scanner, paid service or new Docker pull is required for
the current offline work.

## Current commercial disposition

**NOT_READY, private execution NOT_ADMITTED, verified revenue $0.**
No Mac access, no customer files, no inference or financial actions,
no production change, no draft PR merge and no infrastructure spend.
