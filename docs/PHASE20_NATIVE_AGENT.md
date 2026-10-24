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
workspace is **not established**. All six remaining comparison-arm requests
are still limited to one each under the original eight-request experiment.
