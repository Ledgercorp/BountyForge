# Phase 6 runtime acquisition: pinned digest kind correction

Date: 2026-10-22 UTC. Status: **NOT_ADMITTED**.

## Material finding

The literal image configured in `bountyforge/curated_docker.py` is
`python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590`.

The public Docker Hub layer listing associates **that exact digest** with
the **Linux/AMD64 image manifest** for the historic
`python:3.11.17-slim-bookworm` release. It lists a *separate*
multi-platform **index digest**, `sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89`.

Source:
https://hub.docker.com/layers/library/python/3.11.17-slim-bookworm/images/sha256-8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590?tab=layers

**This webpage is public catalog evidence, not an independently verified
publisher signature or proof that historic layer bytes were authenticated.**

Phase 5 required `verify_oci_manifest_chain` to receive an OCI *index*
under the pinned digest. That assumption was wrong for this image and
made otherwise valid platform manifest receipts impossible to accept.

Phase 6 adds `verify_pinned_image_reference`, which handles either a
pinned multi-platform index OR an exact platform-specific manifest.
Both paths independently verify the caller-supplied SHA pin, media types,
config digest, Linux/AMD64 platform, descriptor bounds, layer list and
uncompressed diff ID metadata. The direct-manifest path requires its
provided platform manifest bytes to equal the pinned reference bytes;
it cannot silently swap the image.

The read-only `acquire_pinned_python_metadata` now determines the
reference type from SHA-verified bytes and only then retrieves the
appropriate child and config. Its fixed Docker Hub endpoints never use a
mutable tag and do not follow redirects.

The private-job review contract now checks
`pinned_reference_digest`, not a misleading `index_digest`. Its final
state remains `REVIEWED_NOT_ADMITTED` or fails closed.

## Evidence and remaining boundaries

- First isolated hosted registry attempt:
  https://github.com/Ledgercorp/BountyForge/actions/runs/39764078063
  (462 tests; 454 passed and eight existing skips; live public metadata
  returned `UNAVAILABLE_OR_UNVERIFIED` because the old verifier
  rejected a directly pinned image manifest).
- New locally constructed synthetic negatives cover both reference
  types, mutated bytes, wrong config and a real identity check on the
  exact configured image digest.
- A second pinned-image registry acquisition run is required to
  establish which actual public bytes can now be verified.

Even a successful live metadata run still lacks full compressed layer
hashes, uncompressed bytes, trusted publisher signatures, independently
verified build provenance/SBOM and all private job admission requirements.
There is no legitimate basis for allowing customer source execution.

No image has been replaced or upgraded; no production deploy, Mac use,
money spent, paid inference, customer source, signed commercial agreement
or received revenue.
