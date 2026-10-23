# Phase15 — selectable autonomous model profiles and frozen comparison

Checkpoint: `bb0758c5a7ff97746d2aadd0c1ad96b725fd3265`.
Branch: `engineering/revenue-linux-scout-20261021`; PR2 stays draft.

## Implemented before inference

QWEN_LOCAL now has explicit `QWEN_1_5B` (unchanged default) and `QWEN_7B`
(experimental) profiles. CODEX_AGENT remains a separate active-session engine.
Unknown profiles and Codex/profile combinations fail before execution. There
is no fallback across profiles, providers or engines. Task and attempt receipts
bind the selected profile and exact model digest. The existing worker/verifier,
frozen protocols and original five MCP operations are preserved.

SQLite batches persist the selection with a nullable, additive migration;
legacy Qwen batches resolve to the existing 1.5B default. Idempotency rejects
changing a batch's model. Lease expiry, reserved attempts, stop/revocation,
fenced writes and recovery remain enforced. The migration does not clear or
reset any store or budget. Runtime profile availability requires the exact
model and archived executable plus endpoint-reported model path, 2,048 context
and one stream; 7B additionally requires the measured process resource limits.

The generation wrapper tokenizes the model's rendered template before inference
and refuses requests exceeding 2,048 tokens including completion allowance.
It records dispatched completion requests separately from client attempts and
reports sanitized failure stages. Both profiles use the same JSON-safe grammar,
150 completion tokens, temperature zero and 45-second request limit. Neither
model nor prompt can select files, endpoints, tests or commands.

## Owner selection

```
python -m scripts.repair_engine --engine QWEN_LOCAL --model-profile QWEN_7B --case-id weighted-window
python -m scripts.owned_queue create --batch-id owned-trial --engine QWEN_LOCAL --model-profile QWEN_7B --case-id weighted-window
```

Configuration accepts `engine`, `case_id`, and optional `model_profile` only.
Omission preserves 1.5B. The local `dashboard/repair-console.html` exports this
configuration and disables model selection for Codex; it does not execute from
the browser and has not been deployed. MCP preparation/queue creation accept
an optional enum profile, which becomes immutable for that task/batch.

On an already authorized Linux host with the exact assets provisioned, a
credential-free bounded server can be started using:

```
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" python3 -m scripts.local_inference --model-profile QWEN_7B --serve-seconds 120
```

Use another credential-free owner terminal for the repair CLI while it is ready.
The server automatically stops; no persistent host or remote listener is added.
This launcher downloads nothing. Missing assets or a mismatched server fail
closed. The 7B model is not silently substituted for the default.

## Owned developmental comparison, frozen before inference

Three new LeftSock-owned maintenance cases cover reserved-unit state changes,
decoded API response handling/recovery, and weighted time-window aggregation.
Each contains related faulty statements, helper dependencies and eight tests;
all three defective baselines reproduced through the existing twenty-control
Docker admission. Test imports were corrected before freezing to match the
unchanged deterministic localizer; acceptance assertions were not changed.
There are no stored reference patches. `fixtures/phase15/manifest.json` pins
source/tests. `experiments/phase15/comparison.json` pins the three tasks,
implementation hashes, verification contract and budgets before any model call.

The comparison runs sequentially on standard public `ubuntu-24.04`, never a
larger or paid runner. Per model: one separate calibration request at realistic
prompt size, then three tasks, two attempts per task. Maximum fourteen
completion requests total, including resource probes. No Codex-authored patch
enters Qwen attempts. A fresh bounded model process serves each task: two threads,
one stream, 2,048 context, 10GiB address-space cap, 180 CPU seconds, 180 wall
seconds, startup <=60s, bounded log and deterministic termination/cleanup.
An unavailable or over-budget profile is blocked before further task execution.
Only source-valid candidates that pass targeted and fresh Docker replay count.

The pinned Apache-2.0 7B revision/digest/license were rechecked against official
upstream metadata. The non-commercial 3B candidate is excluded. Runtime remains
llama.cpp b11750; no automatic image/runtime/model replacement. Both asset hashes
are checked before every launch. At least two logical CPUs, 12GiB available RAM
and 8GiB free temporary disk are required before downloading. Credentials are
removed from the controller/model subprocesses; Docker retains its existing
network-disabled, read-only, capability-dropped resource-limited boundary.
7B weights are removed after the run and are not saved in a persistent cache.
Small sanitized artifacts retain one day. Repository public visibility and the
standard runner path were verified before dispatch; additional spending $0.

## Pre-inference verification and confirmed defect

Python regression: 701 tests, 692 passed, nine existing skips, no failures.
Node: 8/8. Focused profile, tokenizer, unavailable-backend, resource, queue and
MCP tests passed. Actual Codex MCP discovery/invocation preserved all 18 tools,
original five calls, five authorization refusals and kill/reconnection; the
child environment remained PATH only. No model turn was started by the client.

Native MCP testing reproduced an integration defect: the validator assumed
all published properties were mandatory and rejected the new optional profile.
A regression test failed first. The smallest fix accepts required fields plus
published optional fields while rejecting unknown keys, invalid enums and
missing required fields. The original failed trace and successful recheck are
preserved separately. Valid 7B preparation and an unavailable-profile refusal
were verified through the actual Codex MCP client with zero inference calls.
The existing registration was reused; bootstrap refused its equivalent command
shape rather than overwriting configuration. No Phase9 integration was rebuilt.

## Integrity, admission and remaining gates

These cases are developmental: Codex authored the tasks and can inspect tests.
The GitHub environment list returned zero configured environments; the agent can
edit this checkout and its workflows. No separately controlled verifier/held-out
store inaccessible through those authorities exists. A separate container or
withholding tests from prompts does not establish unseen evaluation. Candidate
Docker replay is independent of inference, not a blind generalization estimate.

Nine prior skips remain unverified (eight namespace/rootfs checks plus an older
opt-in replay); owned Docker checks do not admit customer execution. Publisher
identity/provenance, private security and commercial authorization remain separate
unresolved gates. No customer/private execution, payments, production deployment,
recurring schedule, upstream submission, paid API or new host is authorized.
Spending and confirmed revenue remain $0. Live results are pending; no score is
inferred from unit tests or the Phase14 short resource probe.

## V1 actual measurement and bounded protocol correction

Implementation `e3b359e6d1adbe16c6eb35674ae22e1ae662c5e1` passed hosted
regression [40007722674](https://github.com/Ledgercorp/BountyForge/actions/runs/40007722674).
The first actual comparison [40007714754](https://github.com/Ledgercorp/BountyForge/actions/runs/40007714754)
finished PARTIAL_BLOCKED in 241.023s. 1.5B completed three tasks with zero
verified repairs and six repair requests. Reserved-release introduced a new
read of event before its binding; the source guard rejected it. Response
normalization preserved faulty retry/cursor logic and failed tests; its
equivalent revision was rejected. Weighted-window read weight before binding
and was rejected. No failed candidate became review-ready.

7B passed its 929-prompt-token resource calibration (41 output tokens, 44.117s,
peak RSS 8,042,632 KiB), with selected-model identity and wrong-profile refusal
verified. Its first real request had 989 tokenized input tokens and exceeded
the unchanged 45s completion deadline. No response/proposal was received and
no candidate test ran. The worker stopped, revoked remaining work, closed the
server and removed weights. Two tasks were not attempted. This is an incomplete
7B comparison, **not 0/3 incorrect repairs**. Nine completion requests were
dispatched in total; timed-out completion usage is unknown. Process CPU time
was not collected in V1; hard limits and wall/memory measurements are recorded.

The frozen V1 file and exact raw artifact remain intact. V2 changes only
generation context/instructions and measurement/exit reporting, leaving all
tests, source, validators, model identities, two-thread/10GiB/180CPU-second
limits, 45s requests, 150 output tokens and two attempts unchanged. It removes
duplicated editable-lines/scope/protocol metadata and redundant binding names
(the grammar derives names from the same original source). Description, full
source, exact failure feedback and every statement anchor/end/kind remain.
The prompt becomes task-first and the system instruction is concise. Initial
JSON bytes shrink from 2664/2844/2209 to 2096/2309/1678 on the three tasks.
No source-specific fix or reference solution is inserted. Neutral unit tests
check information preservation. CPU process counters are now sampled and
unexpected exits block continuation. V2 is frozen separately before inference;
reusing these now-exposed tasks remains developmental. No timeout, validator,
resource limit or test was relaxed to obtain a score.

## V2 actual result and final narrow-scope experiment

At `c142cf4a04fd096bb2d21ca954040493e3e2e48a`, hosted comparison
[40009784193](https://github.com/Ledgercorp/BountyForge/actions/runs/40009784193)
finished PARTIAL_BLOCKED in 201.055s. 1.5B again completed three tasks with
zero verified repairs, six requests and no passing targeted suite. It returned
unchanged faulty statements for two cases and invalid if-headers for condition
units on the third. All repeated revisions were rejected. 7B's 795-token
resource request was unavailable after 45.049s, before any repair task was
attempted. It consumed 94.36 observed CPU seconds and 7,976,108 KiB peak RSS,
within existing limits. All servers stopped with no unexpected exit. Eight
requests total were dispatched; the incomplete 7B response has unknown usage.
This is not a 0/3 7B model score. Raw receipts and summaries are preserved.

A final, explicitly smaller envelope selects only the unchanged weighted-window
case (eight unchanged tests, two related defects). Both models receive an
identical hard ceiling of 700 rendered input tokens, 150 completion tokens,
two attempts and all previous resource/verification limits. Its initial prompt
was 545 tokens in V2. JSON outside replacement strings is now compact by grammar;
source statements and code-string whitespace are unaffected. Prior pinned-model
startup/memory/runtime receipts are reused; each new server still verifies the
assets, exact selected endpoint/process, host capacity, live tokenizer limit,
resource caps and cleanup. There is no new unscored calibration inference.
Maximum four completion requests total.

This narrows admission instead of extending deadlines or reducing tests. It
does not convert the broader failed resource admission into success. V3 is
frozen separately and remains a one-case developmental microcomparison, never
a new generalization estimate. The experimental owner 7B profile likewise now
rejects rendered inputs above 700 tokens; 1.5B retains its existing full context
ceiling outside this comparable experiment. No default replacement occurs.

## V3 narrow result and allocated-CPU measurement

V3 [40012667306](https://github.com/Ledgercorp/BountyForge/actions/runs/40012667306)
at `6ef293eb7fe12a6602b761b7efef3d99b87063df` ended PARTIAL_BLOCKED in
98.673s. 1.5B generated two compact 21-token no-op candidates and completed
the single case with zero verified repairs. 7B received the same 545-token
initial prompt but its request was unavailable after 45.013s. No proposal
was received or tested; no 7B accuracy score is established. Peak RSS was
7,975,772 KiB; observed CPU time 94.05s; process exit/cleanup were normal.
Compact wire formatting alone did not make two-thread repair inference meet
the deadline. Source/test hashes and all eight test expectations remain fixed.

The traces show two saturated inference threads while the standard free runner
provides four logical CPUs. A final paired single-case configuration uses all
four already allocated CPUs, with unchanged aggregate 180 CPU-second hard
limit, 10GiB address-space cap, 180s process wall cap, 45s requests, 700 input
tokens, 150 output tokens, two attempts, source validators and Docker tests.
No larger runner, GPU, paid capacity or additional host is introduced. Both
models use the same setting. CPU parallelism is constrained to 2 or 4 and must
not exceed observed host capacity; the owner launcher accepts `--threads 4`.
Defaults stay at two threads unless explicitly selected. V4 is frozen before
execution, separate from all previous results. No broader completion or unseen
accuracy is claimed from this smaller workload.

## Final measured outcomes and model decision

**Retain QWEN_1_5B as the default. No verified repair gain from 7B was demonstrated.**
This preserves compatibility, not a claim that 1.5B is commercially adequate.
7B remains explicitly selectable for owned experiments, with a 700-token rendered
input ceiling and no fallback. It is not qualified for reliable repair/revision
within the current CPU/deadline envelope.

| Experiment | 1.5B completed developmental tasks | 7B observed outcome | Completion request attempts | Experiment / whole job seconds |
| --- | --- | --- | ---: | ---: |
| V1, full context, 2 threads | 0/3 verified | First repair request unavailable at 45.049s; two tasks unattempted | 9 | 241.023 / 308 |
| V2, compact context, 2 threads | 0/3 verified | Resource request unavailable at 45.049s; no repair task attempted | 8 | 201.055 / 270 |
| V3, one case, compact wire, 2 threads | 0/1 verified | 545-token repair request unavailable at 45.013s | 3 | 98.673 / 136 |
| V4, same one case, 4 threads | 0/1 verified | One proposal source-rejected; retry ended with process SIGKILL near aggregate CPU cap | 4 | 98.334 / 149 |

V4: [40014549114](https://github.com/Ledgercorp/BountyForge/actions/runs/40014549114),
implementation `f07aef63522534d08bde3dc193950f6f2ec65791`. The 7B model returned
its first actual repair proposal after 43.663s (545 prompt, 60 completion tokens).
It supplied `if ...:` headers for condition-only anchors; the unchanged source
validator rejected it before tests. The retry had 622 tokenized input tokens,
then lost its process after 0.713s. Linux recorded exit -9, 179.8 observed CPU
seconds against the 180-second hard limit, no wall-limit trigger, and peak RSS
8,010,916 KiB. This is strong evidence of aggregate CPU exhaustion. The worker
blocked, stopped the batch and preserved both the earlier source rejection and
failed retry. It never became review-ready. Static inspection also shows the
proposal omitted the denominator repair and would invert the range guard;
those are source observations, not executed test results.

Across all runs, 1.5B produced one source-valid candidate (V1 response-normalize),
which failed its targeted suite. Every other 1.5B proposal was ineffective,
repeated, or source-rejected. 7B produced one returned repair proposal and zero
source-valid patches. **Zero targeted suites passed, zero repairs were verified,
and zero successful repairs were available for independent replay.** There is
no completed paired repair comparison establishing 7B accuracy. Deadline/CPU
blocks are reported separately from incorrect proposals, not as 0/3 model scores.
The single-case experiments do not establish performance on all three cases.

A separate credential-free process reconstructed the actual source-valid failed
1.5B candidate, rechecked source/scope/bindings/diff/hash, admitted a fresh Docker
boundary and executed eight methods. It independently reproduced the failed
suite (`failure_reproduction_matched: true`, `replay_passed: null`, zero successes).
This is failure confirmation, not a passing repair or synthetic success.

Known returned usage:

| Model | Completion request attempts | Known prompt / completion tokens | Requests with unavailable usage |
| --- | ---: | ---: | ---: |
| 1.5B | 18 | 14453 / 1211 | 0 |
| 7B | 6 | 1474 / 101 | 4 |

These 24 attempts include four unscored resource-probe requests. A POST attempt
is not necessarily completed inference. Tokenized input length is not substituted
for server-reported evaluated tokens on incomplete requests; total token usage
is unknown. No paid inference was used. Memory fit was demonstrated: the highest
observed 7B RSS was 8,042,632 KiB (about 7.67 GiB), below the 10GiB address-space
cap, on the existing four-logical-CPU standard public runner. Load times were
approximately 3–4s for 7B. The configured context is 2,048 tokens, but no reliable
full-budget repair-context throughput or maximum practical context length was
established. The 700-input-token experimental ceiling is a safety restriction,
not a latency guarantee. All recorded processes stopped; the V4 CPU-limit kill
was an operational failure, not normal graceful shutdown. All four disposable
weight-cleanup steps succeeded and no 7B cache was saved.

## Post-measurement correction, explicitly unmeasured

The V4 returned proposal confirmed a condition/statement-format problem shared
with 1.5B. Generation protocol V9 now derives unit kind from the same approved
AST metadata and frames condition values as parenthesized expressions. It does
not strip or salvage model-provided headers and does not supply repair logic.
Assignment/return/other statement rules and every independent source validator
remain unchanged. Invalid headers still fail closed. Neutral regression tests
verify condition framing and derived kinds. Invalid pre-dispatch input also
resets usage state so previous request tokens cannot be reused accidentally.

This correction was implemented **after** measured V4 and has zero live model
calls in this phase. It is not credited with any repair improvement. Its future
configuration is frozen separately as `comparison-v5-unmeasured.json`.
The workflow is restored to manual-only, with confirmation false by default.
Actual manual-dispatch refusal was exercised in
[40013662076](https://github.com/Ledgercorp/BountyForge/actions/runs/40013662076):
the job was skipped, executed no steps and made zero model calls. There is no
recurring schedule and neither PR was merged.

## Engineering acceptance and remaining blockers

Final local Python regression: **716 executed, 707 passed, nine existing skips,
zero failures**. Node: **8/8**. Hosted regression at measured V4
[40014554971](https://github.com/Ledgercorp/BountyForge/actions/runs/40014554971)
passed 713 tests (704 passed, nine skips) and Node 8/8; the later additions cover
post-measurement formatting/accounting. Final-commit hosted evidence is linked
in PR2. Model workflow failures above are genuine admission/repair outcomes;
no test was disabled or false success returned to make them green.

Additional reproduced defects fixed during this phase: optional MCP fields were
incorrectly rejected; the bounded server CLI returned success after unexpected
termination; and summaries could omit a terminal inference failure when an earlier
source rejection existed. Each has a failing-then-passing regression. SQLite
legacy-schema migration additionally preserves exact job/batch data, stop state,
lease recovery and the original four-batch lifetime limit. Original five MCP
calls/refusals, 18-tool inventory, PATH-only child, kill/reconnect and profile
handoff/unavailable-model behavior were verified through the actual Codex client
without launching a model turn. The source-selected profiles, CLI configuration
and local browser configuration export are operational; 7B repair quality and
reliable revisions remain unqualified.

Implementation commits:

* `e3b359e6d1adbe16c6eb35674ae22e1ae662c5e1`: profiles and asset/process identity,
  queue migration, MCP/CLI/local-console selection, new frozen owned fixtures,
  bounded runtime/context transport and first comparison.
* `c142cf4a04fd096bb2d21ca954040493e3e2e48a`: task-first compact context,
  CPU/exit measurements, evidence validation and separately frozen V2.
* `6ef293eb7fe12a6602b761b7efef3d99b87063df`: narrow 700-token paired scope,
  compact wire grammar, exact model-authorship checks and V3 evidence.
* `f07aef63522534d08bde3dc193950f6f2ec65791`: four already allocated CPUs under
  unchanged aggregate limits, explicitly selected by `--threads 4`, plus V4.
* Final evidence/formatting commit: V9 unit-tested correction, unmeasured future
  configuration, manual-only workflow, actual V4 receipts and this acceptance
  ledger. Its exact HEAD and CI are recorded in PR2 and the phase completion report.

Changed files are the existing repair/MCP/queue wrappers, new model-profile/runtime
and evidence modules, owner CLI/console, owned Phase15 fixtures, bounded workflow,
focused tests and this evidence directory. Core `worker.py`, `lineedit.py`,
`statements.py`, `model.py`, earlier fixtures and frozen evaluation files remain
unchanged. All Phase15 task/test bytes remain unchanged after the V1 freeze.

Unresolved: no demonstrated 7B verified gain; no practical bounded revision margin;
V9 is unmeasured; no enforceable unseen controller; nine prior security/optional
skips; incomplete publisher/runtime/private-execution admission; no commercial
quality/consent/payment/launch/delivery authorization. A completed paired evaluation
with source-valid model candidates, fresh Docker passes and bounded successful
revisions is required before reconsidering the autonomous default. True unseen
claims require a separately controlled verifier inaccessible to this agent.

Current classification: ENGINEERING_READY_FOR_REVIEW for the owned controls and
evidence. Private execution NOT_ADMITTED; commercial activation NOT_AUTHORIZED.
The active-session CODEX_AGENT pathway is preserved. No production/dashboard
deployment, payments, customer/private source, external submission or new host.
Additional spending $0; confirmed revenue $0.

Machine-readable details, per-attempt hashes, exact usage, observed CPU/RSS,
Linux exit status and whole-job timing: `evidence/phase15/acceptance.json` and
its linked raw comparisons, summaries, replay and Actions job metadata.
