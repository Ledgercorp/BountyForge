# BountyForge acceptance — 2026-10-21 UTC

**DRY_RUN_READY** for bounded internal owned-fixture repair. **NOT_READY** for
real paid bounty operation. No recurring repair schedule or external submission.
Main remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`; PR #1 stays draft.
Required historical commits are preserved. No Mac access or unrelated project edits.

| Verified source | Execution and outcome |
| --- | --- |
| `026e85d766ac9b9e732ae9c1b739e4bd1effbe0e` | [Historical shared-line run](https://github.com/Ledgercorp/BountyForge/actions/runs/39590337663): 5/5 baselines, 12 calls, 0/5 repairs |
| `4eff34d8e09be4687fac4322d294f8128e575dd0` | [Historical symbol/enum run](https://github.com/Ledgercorp/BountyForge/actions/runs/39592095298): 5/5 baselines, 12 calls, 0/5 repairs |
| `28ec65d017d3e755a86652e1d8d6fcd92e08ea9c` | [First durable internal cycle](https://github.com/Ledgercorp/BountyForge/actions/runs/39591802636): all four jobs passed |
| `4eff34d8e09be4687fac4322d294f8128e575dd0` | [Second cycle](https://github.com/Ledgercorp/BountyForge/actions/runs/39592153607) passed; [duplicate](https://github.com/Ledgercorp/BountyForge/actions/runs/39592910695) skipped inference |
| `e3161fff96a8cb45af45c73e7f7e0c191893a8e1` | [Hardened cycle](https://github.com/Ledgercorp/BountyForge/actions/runs/39593624581): 179 cases, 7 skips; 6 harness tests; 4 Node tests; 16/16 scenarios; isolated Qwen repair and durable completion |
| `abef9009878b1b83b88c392526ee45148e453a44` | [Original CPU compatibility](https://github.com/Ledgercorp/BountyForge/actions/runs/39594116526): canary and 3/3 original synthetic repairs passed |
| `89f5e8738e68265b1c08d3fcda6279226509ba81` | [Controlled interruption](https://github.com/Ledgercorp/BountyForge/actions/runs/39594818372): expected exit 75 after live stale-write rejection and durable lease; zero inference |
| Same `89f5e8738e68265b1c08d3fcda6279226509ba81` | [Recovery](https://github.com/Ledgercorp/BountyForge/actions/runs/39595024636): next workflow reclaimed attempt 2, repaired with Qwen and published verified evidence |

Four complete hosted internal cycles are durably recorded, alongside 33
unverified discoveries. Recovery evidence and sixteen scenario results are
committed under `evidence/hosted-*.json`; they outlive short Actions retention.
Historical tasks and acceptance tests are unchanged from recovered HEAD.
No manual solution is counted. Full upstream Boltons tests have not run.

Final local worktree validation: **180 unittest cases, 7 skipped (173 executed
passes); 7 benchmark harness tests; 4 Node tests; 16/16 operational scenarios**.
The seventh harness test verifies fully blocked admission records zero model
attempts and never labels the run real inference. New artifact paths use a fresh
run directory, preventing a failed preflight from uploading an old tracked score.
Model-call accounting occurs only when the model client is actually invoked.
Those reporting guards introduce no new historical repair measurement.

The original run's exact denial was `/proc/self/uid_map: Operation not permitted`.
A current public Ubuntu runner snapshot shows AppArmor restriction=1, namespace
creation=1, max namespaces=58121, no effective capabilities and host seccomp=0.
It was collected on image 20261018.339.1, distinct from the original image;
therefore it supports a policy diagnosis but cannot identify the historical
LSM audit rule. Policy was not changed and unshare was not retried. The policy
receipt records the PR test-merge SHA; no claim it is the branch HEAD.

Live Docker controls verified: immutable official Python digest, network and
model-loopback denial, unprivileged UID, dropped capabilities, no_new_privs,
seccomp, denied root/source writes, no host credentials/socket, memory kill,
no swap, bounded tmpfs with noexec, CPU/PID cgroup readback, output cap, wall
clock timeout and confirmed cleanup. Added imports, dynamic calls, filesystem/
process APIs and introspection payloads are rejected by the line validator.
Seven namespace/rootfs tests remain skipped; arbitrary hostile-code certification,
exhaustive kernel-escape review and CPU/PID pressure stress testing are absent.
No browser rendering claim; API access and frontend syntax/projection were tested.

The existing private Hatchable dashboard is deployed at **v11**, with admin 200,
anonymous 401 and ordinary-member 403 verified. It reads only public GitHub data,
exposes ledger blob SHA/observation time and separates internal cycles from real
bounties. Existing read-only Hatchable discovery remains scheduled separately.
No new service, credential, visibility change or repair cron was introduced.

Infrastructure used: Codex Cloud Linux, standard public GitHub-hosted Ubuntu,
existing GitHub storage/cache and existing personal Hatchable project. New model
cache writes were avoided in the operational workflow. Additional purchases and
paid inference **$0**; confirmed revenue **$0**; invoices not independently audited.
Authorized external writes were confined to this repository's engineering/data
branches, internal PR metadata and private BountyForge dashboard deployment.
Outside PRs, bounty claims, messages to maintainers and commitments: **0**.

Remaining gates: historical repair reliability is still 0/5; no independently
verified funding/AI-participation/eligibility record qualifies a real candidate;
current arbitrary third-party repositories have no admitted execution route;
full upstream regression is absent. Main/schedule activation remains gated.
Specific external submissions always require owner approval. There are no real
review-ready candidates to present or submit.
