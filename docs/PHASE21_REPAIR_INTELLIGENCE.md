# Phase21 repair intelligence: engineering and experiment ledger

**Measured outcome: no autonomous repair-accuracy improvement.** On four new owned
problems, external Qwen, native SDK Qwen and diagnosis-first SDK Qwen each verified
0/4 with equal two-request limits. Granite verified none: one complete case and
three incomplete resource/protocol cases. All 32 authorized completion requests
were used. The default is unchanged; diagnosis remains experimental. A later
native vocabulary-only test verifies two wire-contract fixes, not new AI repairs.

Baseline: `c21d6c7e0500e27995804e69ae74f1ed9e1c9ad5`, draft PR8.
New branch: `engineering/phase21-repair-intelligence-20261024`.
Main and every earlier draft PR are preserved. No deployment, schedule, customer
execution, financial operation, paid inference or external submission is authorized.
Additional spending and confirmed revenue remain $0. Commercial status NOT_ADMITTED.

## Evidence-backed Phase20 diagnosis

`evidence/phase21/phase20-diagnosis.json` binds the six original comparison
receipts. All six proposals passed scope/source capability validation. Native
optional-setting added a None conditional but retained truthiness fallback,
preserving all four baseline failures. Native reading-groups kept a truthy
filter and used a comprehension name against an unrelated outer value; the
external candidate explicitly excluded numeric zero. Both introduced the newly
reported test_zero failure. Both reserve-release proposals left the status guard
unchanged and replaced accumulated state with repeated assignment/increments.

These six responses ended normally at 24–78 output tokens, below the 150-token
limit. Their failures are not demonstrated output-budget exhaustion. Full source
and helpers were supplied; missing source context is not established. The SDK
added 26 required working-directory tokens; a causal accuracy effect is unknown.
Earlier SDK token-clamp/tmpfs failures were fixed in Phase20 and are not repeated.
A new framework alone is not evidence of better reasoning.

## Implemented treatment and compatibility

The opt-in response contains compact diagnosis (authorized anchor, cause enum,
expected behavior <=64 characters, risk enum) followed by the unchanged bounded
changes protocol. This is actionable summary, not an unbounded reasoning transcript.
It shares the same generation request and output allowance with the patch. A
strict parser rejects duplicate/unknown keys, unauthorized anchors and malformed
fields, then extracts only the actual model-authored changes. It supplies no fix.
Existing AST, binding, capability, repeated-candidate and Docker gates stay authoritative.

Retry packets distinguish persistent baseline failures, newly reported failures,
and failures no longer reported. Assertions are bounded, control characters are
removed, and raw logs/unknown fields are not copied. Observation data is explicitly
untrusted; it grants no command or file authority. Source-rejected candidates
have unknown test comparisons, not invented continued failures. Previously
validated siblings are retained by the existing algorithm for all arms and the
complete effective proposal is revalidated. Raw and effective proposals are recorded.

Four new LeftSock-owned maintenance contracts cover shipping totals, cache refresh,
parameter parsing and inventory adjustments. Each has eight fixed regression
methods and two interacting defects. There are no reference patches. Baselines
reproduced assertion failures in the trusted Docker verifier before inference;
source/test and manifest hashes are frozen. The engineering agent can read these
files: this is exposed developmental evaluation, never unseen accuracy. Model
containers receive only the approved source/description/feedback, not test files.

Compatibility testing initially caught two regressions in the old CLI/MCP inventory
expectations (22 instead of 18 tasks). The correction explicitly gates the new
catalog with `RepairService(owned_quality=True)` in the trusted experiment controller.
Default CLI/MCP inventory and original tool schemas remain unchanged. No historical
test expectation was relaxed. The new catalog is hash-pinned and contains no
caller-selected source paths. The controller adds exclusive per-arm claims, a
single worker lock, published-result fencing, SIGTERM finally cleanup and an
independent 180-second SDK lifetime. Unknown/interrupted usage is never refunded.

## Frozen comparison and resources

The main experiment has four tasks and EXTERNAL_BASE / SDK_BASE / SDK_DIAG arms:
at most two requests per engine/task arm, 24 total. The separate optional Granite
trial allows two requests per task, eight total. Both plans freeze implementation,
source and test hashes before inference. Shared limits: context 2048, input <=1898,
output <=150, temperature zero, model 2 CPUs/64 PIDs, 45s request, 180s process
wall/CPU limit, independent targeted plus fresh Docker verification. SDK remains
1 CPU/192 MiB/32 PIDs. Qwen model remains 3 GiB; optional Granite explicitly uses
5 GiB with no swap. All roots/workspaces are read-only, tools absent, seccomp and
no-new-privileges active, no Docker socket/credentials, and only private loopback
in a network-disabled namespace. Model and SDK have separate filesystem/PID/cgroups.

Native SDK keeps required working-directory context and prior-turn history;
external mode has no SDK history. This unavoidable prompt difference is recorded,
not passed off as exact prompt equivalence. Diagnosis consumes some of the same
150 output tokens; truncation is measured rather than silently raising the cap.
First-attempt and retry-assisted outcomes will be reported separately.

Before any launch the controller checks actual outer cgroup CPU/memory and reserves
model cap plus SDK cap plus 512 MiB headroom. It does not rely on a larger host RAM
display. Only this run's cold staged model file pages receive normal cache-release
advice between arms. No system-wide cache or cgroup limit is modified.

## Stronger-model admission

Fresh official Hugging Face metadata confirms IBM Granite 4.2 3B Q4_K_M, revision
`c40945d71cd90f249a56985e8155551a9188dc30`, Apache-2.0 declaration, 2,244,011,552 bytes,
SHA256 `e0406663965846ae22a403456eb826ccce5f450840491f71952f18a7cb78e7d5`.
Pinned runtime stays llama.cpp b11750. Its actual contained help supports the
chat-template kwargs used to disable thinking. Prior owned trials loaded Granite
with about 3.89 GiB process RSS but established no successful repair. Provenance
is official-publisher metadata plus mandatory actual GGUF digest verification;
there is no signed conversion attestation or private-execution clearance.

Qwen3.5 4B Apache-2.0 metadata was also checked; earlier measured contract failures
and roughly 4.54 GiB RSS do not justify another speculative download. Qwen 7B's
roughly 7.5 GiB load and previous CPU-cap failure are poor fits for this 8 GiB
Cloud cgroup. Qwen3.5 9B remains deferred. Model weights are not downloaded merely
to probe an endpoint. No provider account or paid fallback is used; Groq remains
unauthorized. The default remains QWEN_1_5B.

Granite currently fails the conservative Cloud headroom gate. Its separately
frozen trial may run once on an eligible public standard Ubuntu GitHub runner,
after model-free CI and actual capacity admission. Only the one official model,
unchanged small runtime and verified libgomp package may be acquired as inert
bytes. No installer/lifecycle script runs on the trusted host. Model identity,
license and digest remain distinct; Granite is never mislabeled as Qwen.

## Pre-inference verification checkpoint

Live Phase21 model requests so far: **0**. Accuracy: **unmeasured**.
Focused Phase20+21 checks: 33 passed (11 new Phase21 tests). Full regression:
**835 executed, 826 passed, nine existing namespace/rootfs skips, zero failures**
(30.448s). Node: eight passed. Actual hardened SDK/gateway protocol acceptance:
PASS using explicitly simulated responses, zero real model requests and zero
repair successes. The SDK and provider boundaries/tools stayed restricted.
Historical fixtures, frozen partitions and receipts were not changed.

## Cloud launch admission and alternate execution route

The first launch at `8c44500` was denied after staging and before any model
container or arm claim. Actual requests: zero. Staging raised outer cgroup use
from 3,717,570,560 to 5,229,105,152 bytes against an 8,589,934,592-byte limit.
The unchanged required reserve is 3,959,422,976 bytes (3 GiB model + 192 MiB SDK +
512 MiB headroom), more than remained. A model-free real-file experiment found
both advice-only and fsync-plus-advice ineffective; no such workaround was added.
The original plans and the failed resource hypothesis are preserved under
`evidence/phase21/pre-inference-v1/`, `cloud-admission.json` and
`staging-memory-diagnosis.json`. This is not a 0/4 model result.

Before any inference, V2 adds only explicit acquisition of the existing baseline
GGUF to the trusted inert downloader, for an eligible standard public GitHub
runner. Model prompts, tasks, scopes, validators and inference budgets are unchanged.
Qwen's official revision is f86cb2c1fa58255f8052cc32aeede1b7482d4361 and its existing
1,117,320,768-byte artifact SHA remains cc324af0…bb046. No local model is replaced.

The V2 Qwen plan SHA256 was
`fb5543a918246dc5f1ab723366393a16c56f60fde92760bb664586c68fc17f3a`;
the V2 separate Granite plan SHA256 was
`cf4fe0e37f8958ca6147036b7efe8f4cec31607a57d1f77e81e8ccb7a510d480`.
Each binds 46 exact implementation/task files. On the authorized draft PR's first
opened event only, after model-free regression and actual CPU/memory/disk admission,
a standard Ubuntu 24.04 runner may execute the two fixed experiments sequentially.
The job has read-only GitHub permissions, no persistent checkout credentials,
no provider secrets, no cache writes, a 25-minute timeout and at most one active
inference process. Synchronize/reopen/rerun events cannot launch fresh inference.
Small sanitized JSON artifacts have one-day retention; newly acquired weights
are removed. If capacity or public asset access fails, preserve a blocked result.

## Hosted root-cgroup portability correction before inference

Draft PR9: https://github.com/Ledgercorp/BountyForge/pull/9
Initial run https://github.com/Ledgercorp/BountyForge/actions/runs/40108608162
passed model-free regression (835 tests: 826 passes / nine skips), Node and real
isolated SDK protocol QA/replay. Its model gate was BLOCKED, not successful
inference: `/sys/fs/cgroup/memory.max` was absent and every model step was skipped.
The downloaded capacity artifact confirms **zero model requests and no model assets
acquired**. No repair score is assigned. The raw JSON and diagnosis are preserved.

Official Linux cgroup-v2 documentation specifies cpu.max and memory.max on
**non-root** cgroups. The previous reader incorrectly assumed the mount root was
the process's effective location. The fix resolves `/proc/self/cgroup`, validates
the v2 controller layout, reads every visible ancestor, and takes the strictest
numeric limit/headroom together with host MemAvailable and CPU affinity. Unknown,
unreadable, escaping or missing process layouts fail closed. Root-level absent
max files are distinguished from unknown state using kernel v2 identity; no
container resource limit or verifier security check is removed. Three new tests
cover inherited limits, legitimate root layout and invalid observations.

This source-grounded V3 is frozen **before any model response**. Both V2 plans
remain under `pre-inference-v2/`. Final Qwen plan SHA256:
`6ff122f2d457bbe1cac42d843ab82f6ae711c2036cf6e0aa6d0e64ad24fe84fe`.
Final Granite plan SHA256:
`dcdedf899f342d9e1c96d2cec3a2b88c1392517d3b5f1863416205b9ac852912`.
Prompts, tasks, tests, verifier and the 24+8 request ceiling are unchanged. The
workflow permits exactly one synchronize continuation directly from the verified
zero-inference head 2576e2f, run attempt 1 only. Later updates/reopens/reruns cannot
start inference. It never reclaims a spent arm or infers a free provider quota.

## Actual frozen V3 results

Generation source: `112d53842814d26d7b63ec6021869640f144697f`.
Hosted experiment: https://github.com/Ledgercorp/BountyForge/actions/runs/40109689533
The regression job passed (838 tests, 829 passed / nine skipped, Node eight).
The experiment job deliberately remains **FAILED/INCOMPLETE** because three
Granite cases were blocked. A green model-free regression is not a repair score.
There was no rerun of these spent experiments.

| Arm | Cases attempted / complete | Source-valid proposals | Verified repairs | First / retry successes | Actual requests |
|---|---|---:|---:|---|---:|
| External Qwen baseline | 4 / 4 | 3 | 0/4 | 0 / 0 | 8 |
| Native SDK Qwen baseline | 4 / 4 | 3 | 0/4 | 0 / 0 | 8 |
| Native SDK Qwen diagnosis | 4 / 4 | 0 | 0/4 | 0 / 0 | 8 |
| Native SDK Granite diagnosis | 4 / 1 | 0 | 0 verified; 3 incomplete | 0 / 0 | 8 |

All four tasks used their two-request allowance in each arm. There were six
source-valid but test-failing proposals, thirteen source/handoff/diagnosis
rejections and eight repeated proposals among the 27 controller-recorded
handoffs. Two additional truncated Granite responses were captured at the
gateway but not admitted as controller handoffs. Three other requests timed out
without returned usage. These are **32 actual requests / 29 returned model
responses**, not 32 completed repair attempts or sixteen distinct problems.

The existing no-op and repeated-proposal guards worked; no replacement critic
or weaker validator was introduced. Qwen still misread conditional logic,
copied baseline-equivalent code, duplicated branches and repeated ineffective
edits after feedback. The diagnosis treatment often restated the faulty source
instead of describing the intended correction. Its parser rejected mismatched
diagnosis/edit anchors; source gates rejected control characters and control
flow embedded at an assignment anchor. All Qwen diagnosis replies ended below
the output cap and context admission ceiling. More tokens alone are not an
established explanation for those failures.

The treatment also changed system text, dependency facts and anchor presentation
order relative to the baseline prioritized packet. This is a comparison of the
implemented treatment, not a causal diagnosis-only ablation. No broad conclusion
about all structured reasoning or model generalization is warranted.

Granite's three blocked cases included completion-route TimeoutError and
150-token truncations. In shipment-total and cache-refresh, two requests were
consumed during the first controller prompt turn after a timeout; the controller
then refused its strict response-route correlation. In parameter-pairs the first
proposal was truncated and the second request timed out. Request-budget guards
prevented further calls. Subsequent cache-hit counters are consistent with cold
prefill cost, but detailed server-stage timings were not retained. Do not call
these three runs completed model coding failures or claim a complete 0/4 Granite
accuracy measurement. The one complete Granite case produced unsafe source and
then repeated it. Post-turn audits and resource peaks for the three blocked
runs are missing, not passed or zero.

Source/test, model, response, candidate and verifier hashes are retained in all
sixteen original JSON receipts. `failure-analysis.json` classifies each observed
attempt; `model-comparison.json` is reproducible with
`python -m phase21_measurements --output <json>`. No historical candidate, fixture,
expected result or frozen partition was edited after inference.

## Usage and resource measurements

| Arm | Returned prompt / completion tokens | Usage missing | Gateway seconds | Complete-case seconds |
|---|---|---:|---:|---:|
| External Qwen | 4,891 / 632 | 0 | 85.503 | 138.388 |
| SDK Qwen | 7,123 / 536 | 0 | 92.593 | 149.979 |
| SDK Qwen diagnosis | 8,927 / 613 | 0 | 112.359 | 168.579 |
| SDK Granite diagnosis | 4,695 / 644 known | 3 requests | 284.905 | 352.448 |

All 32 submitted inputs were actually tokenized: **29,029 input tokens**. Returned
provider usage totals **25,636 prompt / 2,425 completion tokens across 29
responses**; usage for three timed-out requests is unavailable. Total completion
usage is therefore unknown, not 2,425 exactly. The local format-only QA,
simulated protocol responses, post-hoc manual controls and recorded replay add
zero autonomous-model requests. Supervisor Codex-session usage is not exposed by
these execution tools and is not invented as zero.

Gateway elapsed time totals 575.360s; measured case wall time totals 809.394s.
Wall includes reproduction, startup, model use, verification and cleanup;
verification wall is also recorded per submitted candidate where observed.
CPU measurements cover contained processes through the final probe, not trusted
host-verifier CPU. `resources.json` records each observed cgroup total and peak.

Maximum observed Qwen process VmHWM was **2,045,005,824 bytes**; maximum SDK process
VmHWM was **162,701,312 bytes**, within its unchanged 192 MiB cap. Granite's one
complete case recorded **4,076,965,888 bytes** model VmHWM and 150.441389 model
cgroup CPU-seconds. Its other three cases have no completed peak/CPU measurement.
Cgroup memory.peak and process VmHWM are different; shared file-backed pages can
be charged outside an observed child cgroup. Never substitute configured caps
for measured peaks or missing observations for zero.

Actual eligible hosted capacity was four CPUs, 15,255,166,976 bytes available
memory and 92,088,340,480 free disk bytes before acquisition. Each model still
ran under its own two-CPU quota; Qwen 3 GiB / Granite 5 GiB, SDK 192 MiB.
Only the official Granite artifact was a new model variant. The original Qwen
was restored/acquired with its existing checksum; every model/runtime/library
asset was hashed before execution. No speculative 4B/7B/9B model downloads,
paid provider, GPU or new infrastructure were used. Assets were removed at job end.

## Independent replay and contract feasibility

Fresh credential-free Docker replay reproduced all **21 submitted verifier
receipts**: six failed targeted suites, seven source rejections and eight repeated
proposal rejections. The six tested failed candidates ran eight methods each;
none was promoted. Parser/handoff-rejected text was not executed. Replay PASSED
means original outcomes matched, **not** that the repairs passed. It used zero
new inference and creates zero new model-generated successes. See
`local-recorded-replay.json` and the hash-pinned `origins.json`.

After all model requests were finished, four separately labeled **Codex-authored
manual satisfiability controls** passed 8/8 targeted plus 8/8 fresh tests each
under the same unchanged source restrictions. Each uses two approved statement
edits. This establishes that the tasks admit a passing repair; it is **not** a
Qwen/Granite score, unseen evaluation or model-output correction. No control was
supplied to a model, added to a frozen fixture, substituted for a model candidate
or included in the measured results. See `manual-satisfiability-controls.json`.

## Observed wire-contract mismatches and model-free correction

The measured generator allowed JSON containing a diagnosis anchor absent from
its edits, and control-character escapes that downstream validators rejected.
These were observed in actual proposals, not invented hypothetical defects.
`phase21_wire_contract.linked_diagnosis_grammar` is a separate optional generation
contract: the first edit is linked to the diagnosis anchor, and source strings
use printable raw characters/printable JSON escapes. Existing bounded newline
continuations remain available. Literal backslash escapes inside Python strings
remain expressible. It changes **no** source, binding, capability or test validator.
Duplicate anchors and Python program semantics still require those validators.

A real pinned llama.cpp C API test loaded **vocabulary only**, with native stderr
confirming `vocab only - skipping tensors`; it created no model context, computed
no neural logits/forward passes and made no inference requests. Six neutral
format witnesses were tokenized and checked by the actual native grammar sampler
using synthetic candidate logits. Baseline admitted all three invalid witnesses;
the linked/printable contract rejected all three while retaining three valid
formats, including literal escapes and a bounded multiline statement.

This ran in the unchanged pinned Docker image with 192 MiB / one CPU / 32 PIDs,
read-only mounts, no network/credentials/socket, all fourteen OS checks before
and after, a 35-second host timeout, 30 CPU-second cap and verified cleanup.
The tokenizer/model digest, every runtime-library byte and libgomp digest were
checked. The C API ABI derives from pinned b11750 llama.h (MIT), SHA256
961430f89e2553dbcd99e3e6c59826af9ec143f05911520c74f804d986ff3cd2.
Peak QA process RSS was 72,749,056 bytes. See `native-wire-contract-qa.json`.

This is a **verified formatting-contract improvement**; live repair accuracy is
**UNMEASURED**. It was not used to rerun, relabel or improve the frozen benchmark.
It remains an optional preparation component for a fresh future experiment;
the existing model/worker default is unchanged. The additional native test ran
locally on authorized Linux and is not falsely claimed as a hosted rerun. CI
avoids downloading a full model merely to repeat vocabulary-only QA.

## Final local acceptance and readiness

Full local regression: **845 tests, 836 passed / nine existing skips, zero
failures** (30.120s). Phase21 focused tests: 21 passed; all eight Node tests passed.
Actual process-boundary tests reject missing/unauthorized CLI arguments, preserve
unknown test state, run SIGTERM finally cleanup without refunding reserved usage,
and reject tampered/inconsistent success receipts. SDK/gateway protocol QA uses
explicitly simulated responses and contributes no model repair measurements.

All thirteen complete model arms retained recorded pre/post OS controls; their
SDK sessions recorded actual twelve-tool refusals and normal shutdown. The
three incomplete Granite runs lack final observations and remain blocked.
Cleanup is confirmed for every created model/SDK container. The nine skipped
namespace/rootfs tests remain unresolved security evidence. No hostile/customer
execution or commercial authorization is inferred from owned Docker admission.

The new routine CI runs full regression and exact recorded replay with **zero
fresh model calls**. The frozen experiment's failed/incomplete conclusion remains
published; it is not erased by a later green model-free regression. Later pushes,
reopens and reruns cannot dispatch the spent experiments. Default model remains
QWEN_1_5B; no general repair-quality improvement is claimed. There is no production
deployment, recurring schedule, customer intake/delivery, payment or merge.
Additional spending and confirmed revenue: **$0**. Commercial/private execution:
**NOT_ADMITTED**.

Next high-value milestone: evaluate the linked output contract and more compact
localized feedback on new frozen owned material, with any longer cold-start/
request/output envelope explicitly bounded and matched across comparison arms
before inference. Do not retune these four exposed tasks and call them unseen.
An independently controlled inaccessible evaluation store, stronger hostile-code
isolation/provenance/privacy evidence, reliable commercial recovery, customer
rights, approved payment/delivery procedures and explicit owner launch approval
remain absent. These results do not support accepting paid autonomous work.

Qwen returned syntactically valid JSON in 23/24 responses (external 7/8,
SDK baseline 8/8, diagnosis 8/8); Granite in 2/5 returned responses. This
formatting rate is distinct from six source-valid failed proposals and zero
verified repairs. All these counts exclude timed-out requests with no response.
