# Owned container enforcement review, 2026-10-22 UTC

**Owned fixture Docker controls: 20/20 observed. Private customer source: NOT_ADMITTED.**

GitHub Actions hosted acceptance: https://github.com/Ledgercorp/BountyForge/actions/runs/39713017968
Source commit: cd1722a8a894c15674dfc223f2393c48699a9f67
Full Python regression: 435 tests, 427 passed, eight existing namespace/rootfs skips, zero failures.
Controlled Docker proof: result=observed, reason=none, controls_verified=20.
No Groq calls, no customer source, no authorized payment, no external submissions.

The probe used only the frozen, curator-verified Boltons historical fixture 459.
The existing verify_runtime_boundary function performed multiple finite
security checks inside an ephemeral Docker container using its pinned image
python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590.

Checks included disabled egress and loopback, unprivileged UID, no inherited
API credentials or Docker socket, empty capabilities, no-new-privileges,
active seccomp, 256 MiB memory with swap disabled, max 64 PIDs, one CPU,
read-only root and fixture mounts, bounded non-executable tmpfs, wall-clock
timeout and log limits, verified teardown, plus measured finite CPU and PID
pressure denial inside the same container cgroup.

This does not prove private execution safety: the image producer and the full
dependency/runtime supply chain are not independently attested; a fixed Docker
digest is not itself a complete rootfs tree provenance proof. The actual
private signed-custody snapshot was NOT mounted in this container; customer
source was never accepted or executed. A public GitHub runner and an isolated
Docker container have different privileges; the host-level NOT_ADMITTED
observation and this positive OWNED-FIXTURE result are not contradictory.

The downloaded artifact ID 12398010786 contains the private-host summary,
owned-container-observation.json and read-only prospect report. ZIP digest:
sha256:1aecc6b5af231512f7ee286fe95bdb7ff1060127cd577ea0045b2f9dc1da645d
Only sanitized fields were stored. Provider messages, raw host paths, private
source code, cgroup paths, credentials and Docker stdout were excluded.

New code: bountyforge/private_boundary_review.py validates all 20 trusted
fixed probe controls, image digest and pressure bounds while refusing altered
or missing evidence. It outputs non-authorizing labels only. Its companion
compare_review_only_custody method can summarize previously generated signed
custody metadata but does NOT reopen/verify source bytes or execute them.
Even forged all-true consent/payment flags cannot change admission=false.
Dedicated offline unit tests passed locally before the first GitHub push.

scripts/observe_owned_container.py runs the bounded proof on the one fixed
approved fixture. A failed image pull or pressure control returns a sanitized
blocked observation, not an unsafe fallback. It remains available for a
deliberate later owned-only validation but the one-time step was REMOVED from
routine PR CI immediately after verified acceptance. This prevents unnecessary
future container pulls and noisy automated runs.

Outstanding: secure private host and persistent vault, independently attested
runtime/dependency origin, reviewed kernel/seccomp/ABI and per-job boundaries,
separate customer rights/model-sharing consent, fresh payment, trusted private
custody-to-worker binding, production recovery, delivery authorization and a
statistically meaningful independent real-world repair benchmark.

Both PRs remain drafts, main/dashboard unchanged; paid operation NOT_READY
and verified revenue $0. No Mac, new infrastructure spending, GPU pods,
customer code, paid inference or external jobs were used.
