# BountyForge | hosted CPU acceptance and historical benchmark

Observed October 20, 2026 Eastern / October 21 UTC. This is a measured engineering ledger, not a certification of arbitrary third-party execution or commercial readiness.

## Public repository and control plane

Repository `Ledgercorp/BountyForge` was verified public. Standard GitHub-hosted Ubuntu runners are used. All new model and historical workflows remain explicitly dispatched or gated to a named internal branch and tagged commit, with **no recurring repair cron**. Existing Hatchable read-only discovery remains active separately. `main` was not changed by this engineering branch.

## Accepted

- GitHub-hosted regression on [run 39537924565](https://github.com/Ledgercorp/BountyForge/actions/runs/39537924565): **147 tests passed, 7 skipped**, and **5 benchmark harness tests passed**. The seven skipped tests are not evidence of a certified sandbox.
- CPU acceptance on [run 39536727193](https://github.com/Ledgercorp/BountyForge/actions/runs/39536727193): exact SHA-256-verified Qwen2.5-Coder-1.5B Q4 and llama.cpp b11750, numeric-loopback model, original owned addition canary accepted and 3/3 owned synthetic repair cases accepted. Both structured evidence envelopes verified. No paid inference or external submission.
- Curated Docker boundary on [run 39537540798](https://github.com/Ledgercorp/BountyForge/actions/runs/39537540798): immutable official Python amd64 manifest digest `sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590`. Smoke test verified network denied, source and root filesystem writes denied, checked secrets absent and non-root identity. The container uses read-only source mounts, capability dropping and resource limits.
- GitHub-hosted standard runners rejected unprivileged `unshare -Urnmpf` before code execution. The curated-only Docker route was developed and separately tested as a bounded alternative, not as an unrestricted hostile-code sandbox.

## Historical five-case results

These are five **curated Boltons 26.1.0 source excerpts**, not complete upstream repositories. Each baseline failure was reproduced in the Docker container before a model call. No full upstream regression was run.

| Experiment | Model completion cap | Original baselines | Actual model calls | Verified complete repairs |
|---|---:|---:|---:|---:|
| [Hosted first benchmark, run 39537540798](https://github.com/Ledgercorp/BountyForge/actions/runs/39537540798) | 115 | 5/5 | 10 | **0/5** |
| [Output-budget experiment, run 39537920526](https://github.com/Ledgercorp/BountyForge/actions/runs/39537920526) | 240 | 5/5 | 10 | **0/5** |

The second run recorded model finish reasons, identifying remaining length termination as well as invalid structured edits and targeted test failures. Raising the output allowance did not fix historical cases. Do not relabel these failures as commercial success.

## Authorization and next engineering gate

- **Status: NOT_READY** for unattended compensated bounty repair.
- No external claims, pull requests to outside repositories, payments or signed commitments.
- No Oracle VM, paid GPU, paid inference endpoint or local Mac access.
- Confirmed bounty revenue **$0**.
- Benchmark Docker isolation is for the five already curated historical excerpts only. It is not certified for arbitrary hostile repositories.
- Next: compare another free, open-weight CPU-feasible coding model and/or a more constrained source-line proposal protocol against the *same pinned five cases*, without weakening validation.
- Before enabling recurring actual repairs: require verified real opportunity funding and participation terms, durable cross-run queue, proven safe execution envelope and a separate owner submission gate.

No automatic submission or production scheduled repair was enabled by this work.
