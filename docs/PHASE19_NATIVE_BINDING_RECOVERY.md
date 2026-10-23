# Phase 19: native SDK recovery with an immutable binding cache

Status: **MODEL_FREE_SDK_RUNTIME_VERIFIED** in the authorized Codex Linux
environment. Customer/private execution and commercial operation remain
**NOT_ADMITTED**. SDK acceptance itself measures no model accuracy; the separate
external Qwen developmental repair result is recorded below.

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

### Actual Qwen-authored result

On controller commit `8385181dd96154ee9037bc2d6e10e460d019dac6`, the pinned
Qwen2.5-Coder-1.5B generated its own candidate for the frozen public
`weighted-mix` task. No authored correction, reference solution or model
substitution was supplied. The model response, exact compact prompt, source/test
identities, independent verifier results and resource measurements are preserved
in `evidence/phase19/qwen-owned-handoff.json`.

| Measurement | Actual result |
| --- | --- |
| Development tasks attempted | 1 |
| Completion requests / allowed maximum | 1 / 2 |
| Source-valid model candidates | 1 |
| Targeted suite | 6/6 passed |
| Fresh independent Docker replay | 6/6 passed |
| Verified owned developmental repairs | 1 |
| Detected regressions in that fixed suite | 0 |
| Prompt / completion tokens | 386 / 24 |
| Inference / whole cycle time | 4.341 / 26.341 seconds |
| Runtime load / process elapsed time | 2.014 / 11.648 seconds |
| Peak RSS / virtual address size | 1,896,724 / 2,574,644 KiB |
| Sampled process CPU time | 9.77 seconds |
| Runtime limits | 2 threads, 180 CPU seconds, 180 wall seconds, 10 GiB address space |
| Paid API calls / additional spending | 0 / $0 |
| Native SDK model requests / Codex-authored candidates | 0 / 0 |

Candidate SHA-256:
`003fbcb7f5d3f500d28cd9d9bed9dd254dbb02717222d015a1528a2013b65850`.
Model-experiment receipt:
`d72a3a937c9595bee9f2c656cb238f20e23b4d1d0254cf0de6f08224f2c411ec`.
Trusted verifier receipt:
`2613fe9cea9cba0ab573e0040d1f3178e1f289b92d955a78bbaf8e172673e799`.
The final state is `AWAITING_OWNER_APPROVAL`, with delivery and customer
execution both false. These are hash-bound receipts, **not signed identity or
publisher attestations**. CPU counters are sampled, not exact accounting totals.

This proves one actual Qwen-to-Phase16-bridge repair and two isolated test
executions. It does **not** prove native SDK agent inference, unseen accuracy,
improved generalization or commercial reliability. The test did not need a
second request, so live retry quality is unmeasured here. Previous failed model
comparisons and all frozen evaluations remain unchanged.

The model and runtime were downloaded as inert public data and passed their
existing full checksums before execution. The model is 1,117,320,768 bytes; the
runtime archive is 22,240,456 bytes. The first sequential acquisition timed out
and restarted; that retry was stopped. Four exact HTTP range responses completed
the partial file, followed by the complete SHA-256 check. The successful range
phase took 128.307 seconds; **this excludes the earlier acquisition attempts**.
Network/model acquisition is excluded from the repair-cycle time above. No
private account, paid inference API, GPU or new infrastructure was involved.
The local model process exited cleanly; no new model/SDK container remained.

For separate-host confirmation, `phase19_qwen_replay.py` pins the exact original
model receipt, recreates the same owned task and submits the **unchanged**
candidate through the bridge. It requires its own explicit opt-in, performs no
model request, and requires the same candidate hash plus both Docker suites to
pass. Its CI result is a replay of the existing repair, never another generated
repair. A modified/rehashed candidate record is refused. The PR workflow runs
this without model weights or inference credentials.

After the real CLI refusal scenario was added, the complete local suite ran
**800 tests: 791 passed, nine existing skips** (28.823 seconds). The subsequent
two recorded-replay admission tests also passed. Final hosted counts and replay
evidence will be recorded after publication.

## Implementation inventory and next gate

- `phase17_sdk_bootstrap.py`: immutable-cache admission, staging and safe public-package diagnostic metadata.
- `phase19_native_binding.py`: fixed carrier parsing, ELF/hash checks and sealed cache.
- `phase19_sdk_acceptance.py` and `phase19/runtime_audit.mjs`: real RPC, live tool denial, forced termination/restart, resource and cleanup evidence.
- `phase19_qwen_handoff.py` and `phase19/owned_qwen_experiment.json`: opt-in, fixed two-request local Qwen continuation through the existing bridge.
- `phase19_qwen_replay.py`: exact recorded candidate replay without inference.
- `tests/test_phase17_sdk_bootstrap.py`, `tests/test_phase19_native_binding.py`, `tests/test_phase19_qwen_handoff.py`, `tests/test_phase19_qwen_replay.py`: admission, sanitization, cleanup, subprocess refusal and replay-integrity regressions.
- `.github/workflows/phase19-native-binding.yml`, this report and `evidence/phase19/`: public standard-runner acceptance and sanitized durable evidence.

Native startup is no longer the blocker. The pinned SDK defaults to a DeepSeek
provider; the packaged `dsh-llm-pi-ai` implementation supports explicitly
configured OpenAI-compatible routes, but no local-model transport has yet been
admitted inside the SDK's no-network namespace. Host loopback port 8080 is
deliberately unreachable there. Do not point the SDK at an external provider,
enable host networking or infer account authorization from a configured key.
The next useful SDK milestone is a separately bounded, zero-egress local-model
transport and live candidate turn under the same tool restrictions. The current
external Qwen handoff works without that extra integration. Groq remains blocked
by unverified access, quota and billing restrictions. No commercial status,
production resource, default model, draft state or main history changed.

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
unverified; no provider key is passed to the SDK. Local Qwen's separate resource
and handoff admission passed for the fixed owned experiment above; its candidate
was verified twice locally. Native SDK agent inference remains unmeasured.
The existing skipped
namespace/rootfs tests, private runtime provenance and customer rights/consent
gates remain separate. Revenue and new spending: **$0**. Production deployment,
commercial activation, private execution and customer delivery: **none**.

## Final hosted acceptance ledger

[Run 40042278923](https://github.com/Ledgercorp/BountyForge/actions/runs/40042278923)
passed on `f91585a39d797ef9352a7aad8b220e8e5209bc35`:
**802 Python tests, 793 passed, nine existing skips, zero failures**, plus
**8/8 Node tests**. This includes the MCP, queue/SQLite, provider/CLI admission
and source-validation suites. Runtime acceptance remained model-free and
passed live initialization, tool refusals, shutdown, interruption and restart.

The separate GitHub runner also replayed the actual recorded Qwen candidate
through **two new Docker executions**, both **6/6 passed**, matching candidate
SHA-256 `003fbcb7f5d3f500d28cd9d9bed9dd254dbb02717222d015a1528a2013b65850`.
It had no model weights, provider credentials or inference calls. This
corroborates the **same single developmental repair**, not a second success.
Sanitized durable receipts:

- `evidence/phase19/github-sdk-40042278923.json`, receipt `c198d1f1e8d82a8436165116957833cd411b8e5f66b7061b231c79cbbcecd618`.
- `evidence/phase19/github-qwen-replay-40042278923.json`, receipt `8b928fbf6702a7020ee9bd066a71ad7c7f37d8648f5933bd8ec330e8dd2eb228`.
- `evidence/phase19/acceptance-ledger.json` summarizes exact implementation commits, measurements, restrictions and unresolved gates.

The final workflow path filter covers executable source, tests, fixed runtime
profiles, fixtures and the two evidence inputs used as executable gates.
Report-only updates need not redownload SDK packages or repeat acceptance.
Public-repository and same-branch guards, one active job, read-only permissions,
no checkout credentials and a ten-minute wall limit remain enforced.

**Disposition:** keep the optional SDK recovery and external-model handoff for
engineering review. Do not enable an SDK model provider, replace the default
repair engine, activate production or admit customer execution from these
results. The first useful next milestone is the bounded local SDK-provider
transport described above, followed by a genuine SDK-agent candidate turn.
