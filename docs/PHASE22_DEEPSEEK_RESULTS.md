# Phase22 — real owner-authorized DeepSeek repair results

**Six of six new owned developmental defects repaired on the first attempt.**
All six original model-generated proposals passed eight targeted tests and eight
fresh independent Docker replay tests. There were **six actual completion
requests, zero retries, zero source rejections and zero observed regressions in
the frozen suites**. No reference solution or manually corrected proposal was
supplied. This is a small developmental result, **not independently unseen
accuracy, a matched model-superiority experiment or commercial admission**.

## Authority and provenance

Continuation start: `11c094e14b675dc9cd3726697d9adfcd2131caaa`.
Branch: `engineering/phase22-deepseek-api-20261025`, draft PR10.
The owner answered **Yes** to the explicit <=$2 existing-credit allocation,
>= $20 retained balance and automatic-recharge-disabled confirmation.
`evidence/phase22/owner-approval.json` records that authority without the key or
private grant. Recharge status is **owner-confirmed**, not independently exposed
by the account API. No cash purchase, billing change or commercial action was
approved or performed.

Original frozen plan SHA256:
`a12648b59de913b18d358e94d2cd6abc482c6c86086765871bf52c8bef27b322`.
Every generation/source/test pin matched before and after inference. The six
cases and 48 verification tests were committed before the API experiment. No
generation source, prompt, fixture, test, validator or limit changed during the
trial. `owner_spending_authorized:false` in the frozen plan describes its original
proposal state; the separate private owner grant activates the unchanged plan.

Exact original execution bytes: `evidence/phase22/deepseek-pro-trial.json`, SHA256
`bed6ea807c295632684bcd4a0a9cd6c68f575e52fe7249e971dbe64f0c99d955`;
canonical receipt SHA256
`8f2118eb288509e9e9488821efd3b0d191736cee9480f90f36f86b64e328547a`.
The separately sanitized private-ledger export binds every unique request ID,
case, attempt, reservation, returned usage and accounted cost. These are local
hash-bound receipts, **not provider-signed attestations**.

The API broker alone authenticated. Credential bytes traveled from the exact
owner-designated Drive file through trusted memory/anonymous pipes and were
never written to files, env vars, arguments, prompts, logs, receipts, GitHub or
model-facing containers. No sharing or permission change was made. The trusted
process and pipe exited/closed after the run. The retained private budget store
contains no API key; its grant fingerprint/ledger remain private and gitignored.

## Experiment and independently replayed outcomes

Provider: `https://api.deepseek.com`, returned model **deepseek-v4-pro**.
Official documented version: **DeepSeek-V4-Pro-0813**; the API alias does not
cryptographically identify weights. Thinking enabled/high, JSON object output,
<=16,384 estimated input / <=4,096 total output tokens, 120s/request, one request
at a time, <=two per task / twelve overall. No fallback, tool execution, hidden
internal requests or separate diagnostic inference. The external output handoff
was selected to keep the SDK and verifier network/credential restrictions intact.
This experiment is not described as SDK-initiated model inference.

| Frozen owned case | Requests | Targeted | Independent | Outcome |
|---|---:|---:|---:|---|
| discount_checkout | 1 | 8/8 | 8/8 | VERIFIED |
| retry_state | 1 | 8/8 | 8/8 | VERIFIED |
| merge_records | 1 | 8/8 | 8/8 | VERIFIED |
| response_window | 1 | 8/8 | 8/8 | VERIFIED |
| lease_capacity | 1 | 8/8 | 8/8 | VERIFIED |
| batch_outcomes | 1 | 8/8 | 8/8 | VERIFIED |

The actual model corrected the inclusive discount boundary and tax dependency,
retry exhaustion boundary and exponential delay, falsey record identifiers and
version precedence, explicit empty API values and HTTP 204 behavior, exact
resource release and cumulative state, and non-None successful values with exact
retry eligibility. Checkout used three permitted statement replacements; each
other case used two. Existing deterministic protocol decoding/indent handling
remained unchanged; raw returned JSON was passed to the trusted handoff, never
manually repaired or replaced by Codex. Candidate source hashes and unchanged
source/test identities are preserved in every verifier receipt.

Valid source proposals **6**; first-attempt successes **6**; retry-assisted
successes **0**; incorrect tested proposals **0**; invalid proposals **0**;
repeated proposals **0**; newly reported regressions **0**. The last count applies
only to the frozen tests; no claim of complete behavioral coverage is made.
The source validators enforce scope/capabilities/bindings, not universal semantic
correctness. No code was changed outside the approved source function.

`phase22_evidence.py` cross-checks original file-byte/canonical hashes, frozen
plan/task identities, actual provider-candidate equality, usage/ledger linkage,
cost arithmetic, receipt chains and mandatory full targeted + independent
results. Five new negative tests reject rehashed false success, missing/failed
or shortened independent replay, changed candidates, mismatched request cases
and substituted usage. Its `report` and explicit `replay` operations use **no
credential or inference**. A separate local fresh replay reproduced all six exact
candidate hashes and successful outcomes. It adds no new model successes.

## Tokens, cost and remaining credit

Actual returned token usage across all six requests:

- **4,983 prompt tokens**: 1,024 cache hits / 3,959 misses.
- **10,647 completion tokens**, including **10,310 reasoning tokens**.
- **15,630 total tokens**. Reasoning is included in completion, not added twice.
- No missing usage and no unknown-cost reservations.

The durable ledger accounted a conservative **$0.048742** upper estimate using
peak cache-miss input/output prices and per-request rounding. The authorized cap
was **$2**, with a **$20 minimum reserve**. Pre-dispatch full-envelope reservations
were $0.037848/request; only six of twelve permitted requests were needed.

Initial account balance: **$22.88**, all topped-up credit. The immediate final
balance endpoint still returned $22.88; a later authenticated read-only check
returned **$22.85**. The observed displayed account decrease is **$0.03**.
`credit-reconciliation.json` records this separately from the usage-based upper
estimate. Account-wide balances have limited displayed precision; unrelated
activity cannot be excluded and per-request invoiced cost is not exposed. Neither
the initial unchanged balance nor the later delta is relabeled as an exact bill.
No exact provider-invoiced cost is claimed. Latest observed reserve is satisfied.

**Additional cash spending $0; confirmed revenue $0.** The local credit controls
are not a provider-enforced spending cap. No purchase, recharge, payment transfer,
paid infrastructure, new account, GPU or other provider was used.

## Time, resources and autonomous behavior

Full observed repair cycle: **137.623 seconds**. Sum of completion HTTP round-trip
latencies: **89.707s**. Sum of targeted/independent verifier stages: **19.635s**.
Remaining cycle time includes baseline reproduction, admission and metadata.
Per-request round trips: 21.208 / 10.126 / 9.542 / 24.721 / 11.395 / 12.715 seconds.
These are request latencies, not isolated provider compute measurements.

Trusted controller CPU: **0.423s**, peak RSS **23,592,960 bytes** (22.5 MiB).
These exclude remote model and Docker worker compute. Provider CPU/RAM are **not
exposed by the API**; no such resource measurements are invented.

After launch the existing controller selected all six authorized tasks, generated
and verified each proposal and stopped each task on success without human patch
authorship or intermediate instructions. There is no ongoing background worker,
persistent public service or recurring schedule. The trial is now **CLOSED**:
private STOP marker present, nonempty credit ledger retained, no unknown requests.
Unused request allowance is not permission for another task set or fresh trial.
Do not delete/reset the ledger to rerun. Cross-workspace durable account-global
credit enforcement remains unimplemented; no persistent autonomy is claimed.

## Security and regression acceptance

All six tasks reproduced failing baselines before the provider request. Each
candidate used the existing fixed-source/scope/capability checks and two separate
fresh Docker executions. Runtime admission retained all twenty controlled owned
security observations. Containers had no key, provider internet route, Docker
socket, privilege escalation, writable source/root or trusted-test control.
SDK configuration/resources remain unchanged, including 192 MiB and forbidden
tool restrictions. No arbitrary/customer source was executed. Private execution
and commercial admission remain **NOT_ADMITTED**.

Local post-run regression: **881 Python tests, 872 passed / nine existing skips,
zero failures**, 31.250s; **eight Node tests passed**. Existing nine namespace/
rootfs skips remain unresolved. The five new tests verify evidence integrity;
they are not five repair results. Existing MCP, queue, SQLite, isolation and
engine tests remain in the full regression. The routine PR workflow adds exact
recorded DeepSeek candidate replay without credentials or fresh inference.
[Hosted model-free run 40253483382](https://github.com/Ledgercorp/BountyForge/actions/runs/40253483382)
passed on tested commit `2daa4a1ee358dbc77299643f686bdcaf994788d7`:
**881 Python tests, 872 passed / nine existing skips**, 38.905s, plus **eight
Node tests**. Fresh hosted targeted + independent Docker executions reproduced
all six exact DeepSeek candidate hashes and successful outcomes with **zero
new inference**. Existing SDK negative QA and recorded Phase20 replay also
passed. Hosted receipts are preserved in
`evidence/phase22/github-run-40253483382/`. This does not add another six repairs.

## Recommendation and next milestone

The DeepSeek API pathway is a working bounded autonomous developmental repair
backend, and these six cases justify further controlled evaluation. They do not
justify changing the free default, commercial admission or declaring dependable
unfamiliar-software accuracy. Qwen remains the default/local alternative, Codex
remains session-driven, and DeepSeek remains explicit credit-gated operation.

Historical Phase21 Qwen results were 0/4 per condition; Granite had one completed
unsuccessful task and three blocked tasks. These used **different tasks, prompt/
output limits and model environments**, so no controlled numerical improvement
or causal model-only benefit is claimed from comparing the samples.

Next: a larger, separately frozen maintenance evaluation with independently
controlled preparation/verification and explicit cost authority. True unseen
claims still require an inaccessible evaluation boundary; none exists here.
Customer rights/privacy, hostile-code provenance/isolation, durable coordination,
commercial payment/delivery procedures and explicit launch authorization remain
unresolved. No production deployment, main merge, customer work, payments,
external submissions or other LeftSock project changes occurred.

## Published changes and final custody

Post-approval additions are `phase22_evidence.py`, its five evidence-integrity
regressions, the owner/candidate/usage/balance/replay receipts, and the recorded
DeepSeek replay step in the existing model-free PR workflow. `AGENTS.md`, this
report, the implementation report and current acceptance ledger record the
approval and closed trial. The prior model-free acceptance snapshot is retained
byte-for-byte as `pre-inference-acceptance.json`. The frozen generation modules,
source files, tests, plan and core validators have **no changes** from the
pre-inference commit. No model assets or dependencies were added.

Final publication only attaches the observed hosted receipts and documentation,
using `[skip ci]` to avoid duplicating unchanged regression/replay. All PRs remain
draft; main remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`. The private
nonempty ledger and STOP marker remain; no active Phase22 processes/containers or
inference listeners remain. No additional billable requests will be made for
this closed trial.
