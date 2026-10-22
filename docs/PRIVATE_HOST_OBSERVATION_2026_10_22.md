# Hosted Linux private-execution observation, 2026-10-22 UTC

**Disposition: NOT_ADMITTED for private customer-code execution on the ordinary GitHub Actions runner.** Owned offline tests and read-only research remain available.

## Verified acceptance

[GitHub Actions run #39711726776](https://github.com/Ledgercorp/BountyForge/actions/runs/39711726776) at commit f83e6eb880ed79b2f8be3abbcc857e6ed588af77:
425 tests ran, **417 passed**, eight previously known namespace/rootfs skips, zero failures. The existing PR-only research step found zero verified payable prospects and called zero models.

Sanitized short-lived artifact: bountyforge-revenue-research-39711726776, GitHub artifact ID 12397507301. It includes host-observation.json. Source paths, cgroup names, user identity, host identity, raw commands/output, secrets and environment values were not published.

Actual read-only host assessment: observed_host_prerequisites_passed=false. Private execution, customer source, rootfs provenance, custody and production admission all remain false. The failed observations were:

- cpu_quota_usec
- memory_max_bytes
- memory_swap_max_bytes
- no_new_privileges
- owned_namespace_probe_passed
- pids_max
- seccomp_filter

**Interpretation matters:** The GitHub-hosted namespace call was **not attempted**, so its false field means *unverified*, not an additional observed failure. Earlier Codex/Ubuntu UID-map results remain independent evidence. Current-process cgroup values alone do not prove there are no effective ancestor limits. Nor do they describe resource enforcement inside the previously tested digest-pinned Docker sandbox used solely with owned fixtures. Never extrapolate host-process results to independently configured containers.

## Engineering changes

- Fixed the valid unified cgroup-v2 root mapping 0::/ being classified as missing, with malformed/traversal-path tests.
- Added scripts/observe_private_host.py and three isolated tests. It only reads current-process facts and emits the trusted sanitized assessment, with no namespace launch, model call, customer code or financial action.
- Added one sanitized read-only step and observation JSON to the existing two-day CI artifact. There is still only **one** automatic pull-request test run per commit. No extra workflow or recurring task was created.
- The pure reporter was tested in a disposable local Linux stub fixture before the atomic push; GitHub-hosted CI verified the integrated module and workflow.

## Actual next security dependencies

1. Admit an appropriate separate Linux execution environment that enforces per-job memory, PIDs, CPU, IO, network, no-new-privileges and reviewed syscall/kernel boundaries and reliably tears down jobs.
2. Establish independently trusted immutable rootfs/dependency provenance and verify a pinned runtime immediately before each job. The current synthetic rootfs SHA inventory is not a production rootfs attestation.
3. Verify lawful source access and model-sharing consent, fresh payment, private durable storage and revalidate fenced signed scope/custody for each separately authorized execution.
4. Establish reliable real-world repair quality plus owner-approved customer terms, delivery and dispute/refund controls.

A scoped review lease, this host observation, a GitHub-hosted Docker test or a private snapshot does not create an execution capability. Commercial readiness remains **NOT_READY**, revenue $0. Main, both draft PRs, dashboard and earlier frozen benchmarks remain unchanged. No extra infrastructure spend, Mac use, real customer source, paid inference or outside submissions.
