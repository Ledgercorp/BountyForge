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
