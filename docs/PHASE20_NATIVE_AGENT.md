# Phase 20: native SDK with contained local Qwen

Starting point: Phase19 `36ac19e2be9a03838a0da05e21d99b6c4aa222a1`, draft
PR #7. Work is isolated on `engineering/phase20-native-qwen-20261024`; all
earlier branches, draft PRs, main, frozen tasks and verification controls remain
intact. Commercial/private execution remains NOT_ADMITTED.

## Selected transport and frozen experiment

The inference sidecar owns a `network=none` namespace. It runs the original
Qwen 1.5B model and llama.cpp b11750, plus an owned bounded loopback SSE gateway.
The SDK joins only that sidecar's namespace. Neither process gets external
egress, host networking, a published port, a Docker socket, credentials or the
trusted verifier. The SDK retains 1 CPU / 192 MiB / 32 PIDs. The model gets
2 CPUs / 3 GiB memory with no swap allowance / 64 PIDs, 180-second wall watchdog
and 180 CPU-seconds per process. Both roots/workspaces stay read-only and both
use the unchanged noexec 16 MiB temporary filesystem, UID 65534, dropped
capabilities, seccomp and no-new-privileges. Only the model mounts model assets;
neither process mounts test catalogs or reference solutions.

The pinned SDK's packaged `dsh-llm-pi-ai` supports the declared
`openai-completions` route, custom model IDs/base URLs, SSE, output limits and
zero SDK-provider retries. The local alias is `bountyforge-qwen-1.5b`, provider
`bountyforge-local-qwen`. The public literal `local-no-credential` satisfies the
adapter's bearer-field requirement; it is not an account key. No paid provider
or fallback is configured. The SDK's real agent drives requests; the controller
accepts only its actual assistant event, matched to the model stream, before
submitting a candidate through the existing Phase16 bridge.

`phase20_experiment.json`, SHA-256
`f0d86f4b3123709c9da432844e7f84eea0da30b8779a08f5abc873e6b903c040`,
freezes task/source/test identities and budgets before inference. First is the
exposed `weighted-mix` integration case, at most two SDK completions. A subsequent
developmental comparison selects `optional-setting`, `reading-groups` and
`reserve-release`, one completion per engine/arm: at most two total completions
per comparison case, eight for the entire experiment including the initial
demonstration. No reserved partition is changed or used for unseen claims.
All calls retain 2,048 context tokens, at most 1,898 input / 150 output tokens,
temperature zero, the existing scope-derived grammar and trusted validators.

The gateway binds requests to the fixed model/text-only route, rejects tools,
duplicate keys and excessive bodies/tokens, and refuses completions beyond the
budget. It records actual SSE content/usage without altering the model's answer.
The native policy checks the real empty tool registry and all twelve forbidden
tool names before allowing a turn. Independent Docker verification remains
outside the model namespace. The legacy CODEX_AGENT bridge submission label is
a transport capability, not Codex authorship.

## Runtime dependency evidence

An actual contained version probe reproduced exit 127: the pinned Python image
lacks `libgomp.so.1`. The image and SDK were not replaced. Debian bookworm's
`libgomp1_12.2.0-14+deb12u1_amd64.deb` was acquired as inert data. The image's
existing `gpgv` and Debian archive keyring verified the repository InRelease;
its SHA256 index entry verified Packages.xz, which pinned the package's SHA256.
Only the exact library member was extracted without an installer or lifecycle
script and mounted read-only. The pinned llama.cpp version probe then succeeded:
build 11750, commit dd002b91f, GNU 11.4.0, Linux x86_64. Required glibc symbols
reach GLIBC_2.34, compatible with the unchanged Bookworm image.

- Package: 115,772 bytes, SHA256 `48fec46bda7f5b1638b9e959889bfbc20491247d402d120bb152687eb48143d7`.
- Library: 290,392 bytes, SHA256 `f9a9ad78a8dc39c0e90a265ffa551fae6c92a40f360889b44a7e141f9a2adfb1`.
- GCC runtime license: GPL-3.0-or-later with GCC Runtime Library Exception 3.1. The library is not vendored into Git.
- Repository signatures were good, dated July 11, 2026; this is an integrity/provenance observation, not a current vulnerability clearance or private-execution admission.

No model was downloaded or replaced. No package installer, paid service, GPU,
customer workload, production deployment or financial operation was used.

## Execution ledger

Initial focused admission/transport tests: 12 passed after their missing-feature
failures were observed locally. Node console regression: 8 passed. Full Python
regression and actual SDK inference results are recorded as they execute; no
Phase20 model success is claimed by this initial checkpoint.

### First actual native attempt and diagnosed compatibility failures

The frozen `weighted-mix` budget is exhausted: two genuine native-SDK-initiated
Qwen requests, each one completion token, produced truncated `{"` responses.
Both were consumed by real SDK assistant events and rejected by the handoff
validator. No reference patch was substituted and no successful repair is
claimed. `evidence/phase20/native-demo-v1.json` preserves this original failure.

The pinned pi-ai `dist/api/simple-options.js` subtracts a **4,096-token safety
reserve** before computing output allowance. With a 2,048-token local context,
this always clamps the SDK's authorized 150-token request to one token. The
explicit gateway compatibility correction restores **150**, only when the
actual llama tokenizer confirms input <=1,898 tokens and input+output <=2,048.
It records both the unmodified SDK wire request and the admitted token count.
This does not change the frozen output/context budget or weaken a validator.

The post-turn probe also correctly detected a full temporary filesystem.
Model-free replay of the two actual truncated answers reproduced the failure:
the JSONL session backend lazily loads `node-addon-system` for POSIX flock, and
the carrier's pkg `process.dlopen` implementation copies the entire scoped
package tree into `/tmp/.cache/pkg/<binding-hash>/`. After one turn, 467 files
filled the 16 MiB mount and shutdown failed. The source-grounded correction is
to disable the SDK profile's optional **JSONL persistence plugin**, ID `sessions`,
and use its supported in-memory session store. There is no disk writer to lock;
no lock or native-binding check is bypassed. These per-container logs were never
durable across job teardown. BountyForge retains evidence and coordination
outside the agent. No temporary-storage, memory, filesystem-write or network
allowance was enlarged.

The separate replay diagnostic is explicitly simulated provider traffic, **zero
real model requests and zero repair measurements**. After the configuration
correction, two actual SDK turns consuming the recorded partial answers retained
16,760,832 free temporary bytes, all fourteen boundary checks passed before and
after each turn, and shutdown returned exit 0. See
`boundary-replay-before.log` and `boundary-replay-fixed.json` under the evidence
directory. Real model generation is measured separately.

Exclusive private per-arm reservation files now prevent duplicate/restarted
experiments from obtaining another inference allowance. Interrupted arms remain
reserved; automatic budget refunds/retries are prohibited. The hash-bound prior
demo receipt prevents resetting its spent two-request allocation. These local
claims survive process restart in this checkout; continuity on a new Cloud
workspace is **not established**. All six comparison-arm requests were limited to one each under the original
eight-request experiment; their completed results follow below. Published,
hash-validated per-arm receipts now also fence completed arms on a fresh checkout,
even when private reservation files are absent.

### Completed original comparison and separate integration supplement

The original eight-completion plan is complete: two truncated demo responses,
then three SDK and three external-control completions. On the three matched
tasks the SDK verified **0/3** repairs, external Qwen **1/3**. All six produced
source-valid proposals; five failed their owned regression suites. The model,
sidecar resource limits, temperature, grammar, maximum context and 150-token
output cap matched. The SDK supplied an additional required working-directory
context: exactly **26 more input tokens per task**. The observed result does not
establish that this context difference caused the accuracy difference. No
superiority or commercial-readiness claim is warranted.

The proposed task-only V3 assembly hook did **not** remove the required working-
directory context. Real protocol QA caught this before final acceptance. Pinned
SDK `systemPrompt.refreshContext()` restores missing required registrations after
assembly; the successful supplement's actual wire receipt also contains the
26-token context. The ineffective hook was removed. The frozen supplement still
records the original intended prompt revision; this is an explicit experiment
variance, not evidence of task-only execution. No task was rerun and no result
is attributed to context removal. Required SDK context remains intact.

The controller reuses BountyForge's existing source-validated sibling retention
for failed-test retries, then revalidates the complete effective proposal. The
successful supplement needed no retry, so live effectiveness of that mechanism
is unmeasured. These changes are not retroactively applied to earlier results.

`phase20_supplement.json`, SHA256
`fd231562a7cb38fa2fe9c3fd8d5c1e212a366cf476fd973ed4142e5519fcf208`,
separately freezes one existing exposed boundary-maintenance case,
`chunk-count`, and a two-completion maximum for native integration acceptance.
The original eight-call plan and all original task/test bytes remain intact.
The total Phase20 limit is therefore **ten actual model completions**, at most
two per distinct task including both arms of each original comparison case.
The supplement is developmental integration testing, not a fresh accuracy
benchmark or a basis for hiding the failed original tasks. No authored solution
is placed in either prompt or proposal.

## Verified native repair and measured comparison

The supplement ran against the implementation published in `7ef69c3` and used
**one** genuine SDK-driven Qwen completion. The native SDK initialized the local
provider, initiated the SSE inference request, consumed the identical response
in an actual assistant event, and handed its bounded JSON to the existing
trusted verifier. Qwen independently generated the candidate; Codex supplied no
repair output. `chunk-count` passed **6/6 targeted tests and 6/6 tests in a fresh
independent Docker execution**. Final state is AWAITING_OWNER_APPROVAL, with no
delivery or customer authorization.

- Origin receipt: `8be66779f8399b0fff483d610dfa127eb0838177b559a476a935603b5fcb6e2d`.
- Candidate source: `db84da77718bd0119616f572255d96712b90acf15b894ab62c9285cbc82ea5b2`.
- Verifier receipt: `f9c145306334a747459b2d96d7a321e8bf3f06cb2be9b0ecca8c4580bc76e925`.
- Tokens: 321 input / 25 completion. Inference: **3.939 s**; complete case: **26.996 s**.
- SDK cgroup peak: 71,000,064 bytes; model cgroup peak: 834,781,184 bytes.
- Observed SDK/model cgroup CPU: 1.189648 / 10.457613 seconds.
- Normal SDK shutdown: exit 0; both created containers absent after cleanup.

The six original comparison proposals were source-valid. Their actual results:

| Case | Native SDK / Qwen | External Qwen control | Cause |
|---|---|---|---|
| optional-setting | Failed tests | Verified, 6/6 twice | SDK retained truthiness fallback for explicit false values |
| reading-groups | Failed tests | Failed tests | SDK retained truthy filtering and an outer-value dependency; external excluded zero |
| reserve-release | Failed tests | Failed tests | Both tripled the release counter increment |

| Original matched comparison | SDK | External control |
|---|---:|---:|
| Tasks / valid candidates | 3 / 3 | 3 / 3 |
| Targeted and independently verified repairs | 0 | 1 |
| Actual completion requests | 3 | 3 |
| Prompt / completion tokens | 1,500 / 110 | 1,422 / 133 |
| Inference seconds | 18.178 | 17.857 |
| Sum of complete-case seconds | 87.719 | 83.847 |

Together with the two initial truncated requests and the separate supplement,
Phase20 used **9 actual completions: 6 SDK-driven and 3 external**, 4,365 prompt
and 270 completion tokens, 46.944 inference seconds and 229.388 summed case wall
seconds. The one unused supplemental allowance is closed by its completed claim
and published receipt. Nothing automatically refunds a crashed/unknown request.
The initial demo had one resource/protocol interruption and failed shutdown;
this original failure remains recorded. The post-fix cases completed cleanup.

`model-comparison.json` is reproducible with `python -m phase20_measurements`.
It binds all eight original records and separates the paired comparison from
the supplement. Source/test/candidate and response hashes remain in their
original receipts. Both reading-groups candidates introduced the additionally
reported `test_zero` failure. Bounded feedback is not an exhaustive regression
count. No failing candidate was promoted to review-ready.

Memory above is **cgroup memory.peak, not process RSS**. Shared read-only model
pages can be charged outside the observed cgroup. Do not compare these figures
to Phase19 process RSS as if they were the same measure. CPU includes contained
observation subprocesses through the last probe; trusted host-verifier CPU was
not separately instrumented. Complete-case time includes setup, reproduction,
inference and verification; separate verification latency is unavailable.
Initial-failure CPU/memory were not captured. Hash binding is not an authenticated
runtime signature or cryptographic authorship attestation.

## Black Box and independent replay

The real SDK/gateway protocol acceptance uses an explicitly **simulated**
provider, empty model-asset mount and no model execution. Two actual SDK turns
consume the recorded rejected fragment, preserve required context/history, and
shut down cleanly. All twelve forbidden tools are actually invoked and refused
before the first and after both turns. Seven malformed/unauthorized HTTP requests
are rejected; a third otherwise-valid completion is denied before backend
forwarding. The simulator counter remains two. Unknown SDK RPC is rejected.
All fourteen SDK and fourteen provider OS-boundary checks pass, including actual
external TCP denial and loopback-only interfaces. No model or repair success is
counted from these tests. See `local-protocol-acceptance.json`.

The real model sessions have the same pre/post fourteen-control observations
and twelve-tool refusals. Zero tools are exposed, MCP resources are absent,
credentials are absent and optional session persistence is memory-only. The
sidecar and SDK share only the network namespace, not PID/filesystem/cgroups.
The local raw model and gateway ports are private loopback services; this does
not certify the native runtime against arbitrary malicious code or admit
customer workloads. The gateway/SDK guards and independent verifier remain
separate controls.

`python -m phase20_replay --admit-recorded-owned-replay --output <receipt.json>`
replays the exact native chunk-count and external optional-setting successes,
each through targeted plus fresh verification, and confirms the recorded native
reading-groups candidate still fails tests. Origins and candidate hashes are
checked; it makes **zero** model requests and claims **zero** new repairs.
Local replay passed; see `local-recorded-replay.json`. Default-off CLI behavior,
unknown arguments, modified receipts, missing SDK assistant events, tool access,
invalid scope, provider identity and restart budget fences have focused tests.

## Acceptance, operation and limitations

Local final regression: **824 tests, 815 passed, 9 existing namespace/rootfs
skips, zero failures** (31.157 s). The 22 Phase20 focused tests passed; all eight
Node console tests passed. The full suite preserves MCP, SQLite recovery,
queue/cancellation, source validators, historical and frozen evaluation checks.
The skipped checks are not completed security verification.

The new single PR-triggered workflow uses the public standard Ubuntu 24.04
runner, read-only GitHub permissions, nonpersistent checkout credentials, a
10-minute timeout and one concurrency group. It runs full regression, the real
recorded Docker replay and the real SDK with the labeled protocol simulator.
It downloads only the two hash-pinned public SDK wheels as inert data, not models
or installers; receipts expire after one day. There is no schedule, provider
secret or live inference in CI. Hosted results are appended after observation.

Use `python -m phase20_native_agent --help` for explicit admission and frozen task
selection. Current experimental arms are completed and fail closed on reuse;
new experiments require separately reviewed frozen input/budget material.
Existing QWEN_LOCAL defaults, CODEX_AGENT session-driven behavior, console, all
original MCP operations and production settings are unchanged. This optional
native path is **off by default**. Rollback is simply not invoking it; the existing
external/local engine remains available without a framework replacement or
hidden provider fallback.

Private execution and commercial status remain **NOT_ADMITTED**. Deployment and
scheduling are inactive. Additional spending and confirmed revenue are **$0**.
No customer code, payments, external submissions, customer communications, paid
inference, GPU, Mac access, production writes or merges occurred. The only
external writes are the authorized engineering branch, draft PR and CI artifacts.

The integration works, but the paired sample shows no repair-quality benefit;
retain the existing default and keep Harness experimental. A high-value next
milestone is a separately frozen, bounded comparison of stronger admitted local
models or better diagnosis/feedback on new owned development tasks. A genuinely
unseen quality claim still needs an independently controlled inaccessible test
store. Commercial use additionally needs source/model-sharing rights, privacy,
runtime/dependency provenance and vulnerability review, stronger customer
isolation/recovery evidence, fresh payment checks and explicit launch/delivery
authorization. Memory-only SDK conversations are not durable session recovery;
BountyForge's external claims and receipts provide fail-closed experiment custody.
