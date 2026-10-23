# Phase 19: native SDK recovery with an immutable binding cache

Status: **MODEL_FREE_SDK_RUNTIME_VERIFIED** in the authorized Codex Linux
environment. Customer/private execution and commercial operation remain
**NOT_ADMITTED**. No model accuracy was measured by this acceptance test.

## Reconciliation and provenance

Started from the actual PR #6 head
`c8a772998e408243c7913754a24ba649e933d577`, newer than the supplied checkpoint.
PRs #1, #2, #4, #5 and #6 remain draft, with their existing base branches.
This work is isolated on `engineering/phase19-native-binding-20261023`, targeting
the Phase 18 branch. No reset, merge, force push, main modification or deployment.

Recovered Codex model-comparison work remains on the revenue branch: source
commit `e578de96cff642a53d4b676bf8aed87955519876` and its subsequent evidence
commit (see `docs/NEXTGEN_MODEL_EVALUATION.md` there). The completed 18-call
developmental trial produced zero verified repairs; it is not rerun here.
The clean earlier Harness research worktree is preserved separately. Phase 16's
candidate bridge and Phase 17's isolation are reused, not replaced.

## Established root cause

The binding is **present** in the published runtime executable's embedded pkg
filesystem. The upstream loader materializes it into a cache under `/tmp` before
loading it. Our container deliberately mounts `/tmp` `noexec`; mapping the
binding's executable ELF segments from that mount fails.

The diagnostic term `opaque` was introduced by BountyForge's long-token
redaction, not an upstream package identity. The actual public package is
`node-addon-require-builtin-linux-x64-gnu`. The sanitizer now exposes only two
fixed public native-package names in separate metadata, without disclosing
raw stderr or arbitrary package identifiers.

Evidence is in `evidence/phase19/controlled-loader-comparison.json`: the same
binary under the original cache policy reproduced Phase 18's exact stderr
SHA-256 `6fd52d4214eeb7c98d1e5957358a66dd2e12bbab9b650c2c3d69703f4e1cdefe` and
exit-1 native-binding refusal. Selecting the immutable cache produced a real
initialize/shutdown exchange. A separate contained load of the **same binding**
from `/tmp` confirmed `failed to map segment`; that negative probe is repeated
by the acceptance runner. These are actual process results, not mocked RPCs.

Source inspected without host execution:

- [Loader packaging contract, pinned revision](https://github.com/deepseek-ai/dsh-node-addon-require-builtin/blob/a58d3599a2e551d7d706d1ff796c9fd4bbaff63c/docs/packaging.md): documented `NARB_NATIVE_CACHE_DIR`, cache layout, content-hash validation and `getNativeBindingInfo()` checks.
- [Actual loader implementation](https://github.com/deepseek-ai/dsh-node-addon-require-builtin/blob/a58d3599a2e551d7d706d1ff796c9fd4bbaff63c/packages/loader/index.ts): default temporary cache and materialization before require.
- [Matching Harness release](https://github.com/deepseek-ai/deepseek-harness/tree/687f282e8625c6b8d11ff58211a90524be2e4317): Cordis `agent/created` and tool-registry APIs.

The official Node CLI was inspected as a fallback; no Node packages or lifecycle
scripts were installed. It is unnecessary for this fix. The upstream projects
are MIT licensed; no new dependency or license change is introduced.

## Minimal fix and exact release bytes

`phase19_native_binding.py` parses the **hash-pinned** carrier as inert data,
extracts only the fixed Linux x64 N-API v9 binding, verifies its size, ELF
architecture and SHA-256, and seals a new cache read-only. The original carrier
is unchanged. The native loader continues checking its own source/cache hash,
product, backend and ABI. There are no Node patches, loader overrides or
validation bypasses.

| Item | SHA-256 |
| --- | --- |
| SDK wheel 0.2.1rc2 | `30fc72c67f20ff4b46c6952087ea596fc70c2692001aa372185a24f9866bdc46` |
| Linux manylinux_2_28 x86_64 runtime wheel 0.2.1rc2 | `0a0a4eb85a22cd9339972e6a5ced77a27ec791353a5b220e3e10b8cdbbdeca39` |
| Embedded native executable, 316,542,144 bytes | `b6f70327db1392b4ff879b8be26c87349b14933c1b4f7a90b391446bb005aae8` |
| Binding, 295,392 bytes, native package 0.1.9 | `40c34d27d8339e246a8f7415a06152935496cdc06555ea8fce0e052011acc70f` |

Embedded binding member:
`/node/node_modules/node-addon-require-builtin-linux-x64-gnu/prebuilt/linux-x64-gnu-napi-v9.node`.
Only fixed `NARB_NATIVE_CACHE_DIR=/opt/harness/native-cache` is added to the
contained SDK environment. It lives inside the existing read-only payload mount.
Public staging directory traversal is explicitly sealed to mode 0555 so a
restrictive host umask cannot accidentally block UID 65534. The initial local
exit-126 staging-permissions observation was separate from Phase 18's failure.

The same pinned Python image remains:
`python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590`.
No image replacement, layer-integrity rerun or publisher-authentication claim.

## Actual model-free acceptance

`evidence/phase19/codex-linux-sdk.json` records a real hardened runtime:

- Authentic JSON-RPC `initialize` response naming `deepseek-harness-sdk-runtime`.
  The internal RPC server version is `0.0.1`; wheel identity remains 0.2.1rc2.
- Idle session creation through `session/working-directory/get`, without a
  prompt, model request or agent turn.
- Owned Cordis observer queries the **live agent registry**, which exposes zero
  tools. Twelve actual registry execution requests return `UNKNOWN_TOOL`:
  Bash, PowerShell, terminal execution/input, read/write/edit/image-read,
  three MCP resource operations and `run_code`. If any forbidden body exists,
  the observer fails without invoking that body. MCP resource service absent.
- Observer rejects any `agent/request` rather than permitting inference.
- Authentic shutdown response, exit 0 and independently queried empty container
  listing. A Docker daemon failure cannot be counted as cleanup.
- Forced termination after initialization returns exit 137; container removal
  is confirmed. A fresh process then initializes and shuts down with exit 0.
- All 14 existing containment observations pass again. No-network, UID 65534,
  dropped capabilities, no-new-privileges, seccomp, read-only root/workspace,
  no socket, one CPU, 192 MiB memory/swap, 32 PIDs and 16 MiB noexec temporary
  storage remain unchanged. Canary bytes unchanged.

The local acceptance took **15.162 seconds** including staging, probes, failure
recovery and restart. The primary SDK cgroup peaked at **57,626,624 bytes** and
17 tasks, with 749,455 microseconds CPU usage at the sample. This includes the
fixed owned measurement subprocess, excludes the two separate lifecycle
containers and is not a model-inference benchmark.

The profile disables session-log upload and no model turn occurs. Network-none
prevents outbound communication. We do not claim a measured count of attempted
syscalls or an exhaustive security audit of every upstream plugin.

Local regression on the completed implementation: **795 Python tests, 786
passed, nine existing skips, zero failures** (27.584 seconds); **8/8 Node console
tests**; focused SDK/native contracts **16/16 passed**. Seven new tests cover
sanitization, immutable-cache admission, unknown carrier rejection, real-audit
receipt requirements and rejection of false cleanup evidence. Skipped security
checks were not relabeled as passes. Hosted corroboration follows.

### Hosted corroboration

[Run 40040762452](https://github.com/Ledgercorp/BountyForge/actions/runs/40040762452)
passed on exact implementation commit
`e48d75e944e1cf01d12ea891bb7324fa5a67ae42` in draft PR #7.
All 795 Python tests completed (786 passed, nine skipped), plus 8 Node tests.
The **actual live SDK** acceptance passed, rather than merely classifying a
startup refusal. Runtime/negative-tool/cleanup/restart results are preserved in
`evidence/phase19/github-sdk-40040762452.json`; its hash-bound receipt is
`29850a95ff5ae98538d6bc2416723d3bd212c9cbeb3b4fdf74d4be5eb13973a3`.
Acceptance took **7.174 seconds**; the primary SDK cgroup peaked at
57,643,008 bytes and 17 tasks, with sampled CPU usage 746,664 microseconds.
There were zero model requests and no credentials supplied.

### Bounded external-model continuation

The existing local Qwen model is the only inferred-cost-free backend admitted
for this continuation. Access to Actions secret **metadata** was refused with
HTTP 403; Groq access/quota/billing authorization is therefore not established,
and no Groq inference is attempted.

`phase19/owned_qwen_experiment.json` freezes one previously public development
case (`weighted-mix`), exact source/test digests, the original model/runtime,
two completion requests maximum, the existing LEGACY resource envelope,
150 output tokens/request, 45 seconds/request, two threads and 2,048 context
tokens. Its SHA-256 is
`9cbba663265a33043949f3e477d838f12791a7acfeb3d11233c73776a4b0db34`.
`phase19_qwen_handoff.py` uses the existing compact prompt, grammar, local
runtime, revision logic and Phase 16 bridge. It supplies no reference correction
and preserves both Docker test passes as the success requirement.

This is **external Qwen generation through the output-only bridge**, not a native
SDK model-provider integration. The bridge's existing `CODEX_AGENT` submission
capability is a transport/session label, **not** Codex patch authorship; the
controller records `candidate_author=QWEN_LOCAL`, complete model-response hashes
and observed request metadata. The underlying receipt continues to state that
authorship is not attested. No Codex-authored candidate may be substituted.
No model accuracy or successful repair is claimed before the real experiment.
The script requires explicit opt-in, a hash-bound passed live SDK receipt,
credential-free Linux, sufficient local CPU/memory/disk, and the exact existing
model/runtime assets. It neither downloads assets nor selects a remote provider.
Four additional admission regressions passed after reproducing their missing
implementation failures locally; the expanded full suite completed **799 tests,
790 passed and nine existing skips**, zero failures (26.049 seconds). The four
tests establish default-off behavior, an immutable two-request/case budget,
rejection of false SDK receipts and insufficient resource capacity. They do not
simulate a successful model repair.

## Reproduce and rollback

Stage only the exact two public wheels as inert files; do not install them.
On an authorized Linux x64 Docker host with the fixed image present:

```sh
python -m phase19_sdk_acceptance --wheel-directory /absolute/staged/wheels \
  --execution-host codex-session --admit-model-free-probe --output receipt.json
```

The GitHub runner uses `--execution-host github-actions` and the existing host
admission gate. `.github/workflows/phase19-native-binding.yml` runs once per
eligible same-repository PR update, standard Ubuntu only, no secrets, no
persistent checkout credentials, no schedules; small sanitized receipt retained
one day. It performs full Python and Node regression before real acceptance.

Rollback is the isolated Phase 19 commit(s); the older branches remain intact.
Without a valid immutable cache, SDK launch fails closed. No inference or
commercial feature is enabled by this change.

## Remaining admission boundaries

Runtime startup and live tool refusal do not establish an admitted model
provider. Groq access, free quota and billing constraints remain independently
unverified; no provider key is passed to the SDK. Local Qwen remains the primary
zero-paid-API candidate, subject to its separate resource and handoff admission.
No model-generated repair is claimed by these receipts. The existing skipped
namespace/rootfs tests, private runtime provenance and customer rights/consent
gates remain separate. Revenue and new spending: **$0**. Production deployment,
commercial activation, private execution and customer delivery: **none**.
