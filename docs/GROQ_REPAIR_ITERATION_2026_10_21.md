# GPT-OSS repair iteration, 2026-10-21

Status: internal **DRY_RUN_READY**; paid repairs **NOT_READY**. Revenue $0.
Recovered branch HEAD `92ced9c51d5b302a42614d0938d7ee43b7a47cf8` by clean
fast-forward. No merge, reset, dashboard change or synthetic-ledger write.
PR #1, PR #2 and main remain separate and preserved.

## Baseline and precise diagnosis

Canonical run [39677572877](https://github.com/Ledgercorp/BountyForge/actions/runs/39677572877),
artifact `12382877414`, ZIP SHA-256
`82ce41a04bb7ddeecccc69caf7075c0c8b7d3c08eab7af859a8d3dfac0956dca`.
The original report, replay and admission records are archived unmodified in
`evidence/revenue/groq-owned-baseline/`, alongside `failure-audit.json`.
The existing independent evidence gate accepted the recovered report locally.
The already executed Docker replay verified exactly `optional_banner` and
`setting_precedence`; no new model or Docker execution was needed to recover it.

| Owned structural case | Calls | Outcome | Actual cause |
| --- | ---: | --- | --- |
| optional_banner | 1 | pass, replayed | none |
| reference_code | 2 | source rejection twice | new attribute capability; identical retry |
| setting_precedence | 1 | pass, replayed | none |
| empty_summary | 2 | regression error twice | replacement deleted an existing binding; identical retry |

Both failed cases chose the correct approved source scope. All six responses
were completed structured JSON, not provider timeouts or truncation. No failed
case reached a full upstream suite: these are owned regression tests only.
The reference-code prompt omitted the loop values needed to interpret its
assertions. The summary retry received the new exception separately, but its
`previous_error` field wasted its prefix on unittest banner text. These context
limitations are observations, not proof that either caused the model's choice.

Totals: **2/4, six calls, 3,565 prompt / 798 completion / 461 reasoning tokens**.
The recorded 298.360 seconds includes adapter pacing; provider inference time
was not independently recorded. Qwen's canonical structural v5 remains **0/4,
eight calls**, v6 **0/4, sixteen calls**. No baseline is overwritten.

## Opt-in v7 implementation

`ast_contract_v7` uses the same `propose_lines`, line schema and `stage_lines`.
It adds source-derived existing-attribute constraints, complete bounded test
methods (including loop inputs/setup), distinct baseline/latest diagnostics,
and explicit replacement/assignment and untouched-source retry semantics.
Omitted test units are marked incomplete; oversized contexts fail closed.
A JSON-equivalent repeat is rejected before candidate execution.

No known fix or task-specific solution enters the prompt. No source validator,
Docker policy, fixture, acceptance test or line scope is relaxed. V5/v6 prompt
behavior is preserved. Development tests use neutral owned examples rather
than historical repair answers. V7 has **no measured live repair score yet**.

## Verification ledger

- Recovered source: 297 tests, 290 passed, seven existing rootfs skips.
- Red tests for context defects: five methods, two failed, two errored, one
  existing security assertion passed. After implementation and added negatives:
  seven context tests passed.
- Current full local regression: **304 tests, 297 passed, seven skipped**.
- Historical harness: **10 passed**; dashboard: **4 passed**. These are not
  autonomous repair counts. `git diff --check` passed.
- Infrastructure used: Linux cloud checkout and read-only GitHub artifact/API
  access. No new live inference, paid API, customer source or external submission.
- No deployment, repair schedule, public offer, payment or customer contact.
- Seven rootfs checks remain skipped. Arbitrary/private customer code remains
  unadmitted. Free Plan attestation is not an independent billing guarantee.

Next: freeze v7, validate independent historical replay/usage accounting offline,
then at most one bounded hosted historical experiment under the existing Free
Plan authorization. Historical tasks remain unchanged; they are a previously
exposed fixed evaluation set, not newly secret holdouts. Never tune on its
results and relabel a rerun as independent.

## Frozen historical experiment preparation

The existing historical workflow now has an explicit `groq` choice for v7
only, manual dispatch on this feature branch only. Existing Qwen acceptance
and its default backend are preserved. At most eight transport calls, 1,024
total generation tokens per call, 60-second spacing, no retry/fallback after
provider failure, and the unchanged 150-token patch interface/3,000-byte
answer limit. Retry allocation reserves first-attempt coverage for remaining
historical symbols. This differs from the old Qwen protocol/budget, so any
comparison is a system comparison, not an isolated model-size experiment.

The separate replay step has no Groq key. It checks exact revision, model ID,
provider usage, transcript SHA, Docker admission, baseline failures and call
counts before accepting a completed hosted experiment. Successful patches must
also replay the exact sequential symbol scope and source hashes independently.
Previously stashed diagnosis-order/source-binding verifier improvements were
recovered selectively; the remaining stash was preserved.

Local freeze checks: **313 tests, 306 passed, seven skipped**; ten historical
harness tests passed. Five hosted-budget/accounting methods plus one transcript
scope test, and three recovered diagnosis-verifier tests cover negative states.
Workflow YAML and every shell block parsed; actionlint was unavailable. No live
inference during development. `historical-v7-freeze.json` pins the implementation
and original fixture hashes before observing any new historical model output.

## Private review integration

`bountyforge.paid_intake` connects the existing Stripe gate, review ledger and
private CAS adapter through an internal command accepting only a bounded
Checkout identifier on stdin. It refuses known model/publication credentials,
GitHub Actions and unapproved volume configuration. It never accepts source or
dispatches execution/delivery. Fresh payment checks occur even for duplicates.
Six integration tests passed with mocked HTTPS and real ephemeral private
SQLite files; full local regression **319 tests, 312 passed, seven skipped**.
This is not a private deployment, payment verification or customer-code
execution certification. No actual Stripe request or order was processed.

A subsequent durable-write fault injection passed: even after successful mocked
provider checks, a CAS/store write rejection emits no review-ready result and
makes no blind retry. Full local regression is now **320 tests, 313 passed,
seven existing rootfs skips**. The prior 319-case source passed hosted regression
[39681184050](https://github.com/Ledgercorp/BountyForge/actions/runs/39681184050)
at `7acfe00c84c9e5e0bc5d104327f3142332652ad8`. Historical evaluation code remains
exactly frozen at `c2d8f24d2a3e1e5871ac5b654e4ce8db90978d71`.

## Completed independent historical evaluation

[Run 39680884997](https://github.com/Ledgercorp/BountyForge/actions/runs/39680884997),
job `119502751100`, evaluated frozen commit
`c2d8f24d2a3e1e5871ac5b654e4ce8db90978d71`. **1/5 passed, eight calls,
5/5 reproduced and attempted, zero blocked.** Independent credential-free
Docker replay passed exactly case **460**, with its three unchanged excerpt
regression tests. All admission controls, including CPU/PID pressure checks,
passed. This is a model/worker result, not an admission failure.

| Fixed historical case | Calls | Result and precise failure |
| --- | ---: | --- |
| 454 | 3 | second symbol: unexpected indent at candidate line 87; retry falsely deduplicated the already source-validated first symbol |
| 459 | 2 | first candidate: unbound `hnbytes` in zetta test; retry: unexpected indent at candidate line 26 |
| 460 | 1 | **pass**, independently replayed |
| 475 | 1 | complete assignment substituted for one physical line left a continuation; unexpected indent at line 5; retry budget reserved |
| 524 | 1 | five physical replacement lines exceeded unchanged three-line limit; no retry budget |

All eight responses finished normally. No inference-limit truncation or
provider error was recorded. Model usage: **8,627 prompt + 3,284 completion =
11,911 total tokens**, including 2,681 reasoning tokens within completions.
Adapter wall time including rate waits: **419.444 s**; GitHub job: **451 s**.
Pure provider inference duration is unavailable. No cost amount can be inferred
from token usage: Free Plan is owner-attested, billing independently unresolved.

Before/after on the original fixed five tasks: Qwen v5 **0/5, twelve calls**
([39599906768](https://github.com/Ledgercorp/BountyForge/actions/runs/39599906768)),
GPT-OSS v7 **1/5, eight calls**. Prompt protocol, backend and retry allocation
changed, so this is a system comparison. The historical cases were previously
exposed, not newly secret holdouts. Fixtures, defects and tests are unchanged;
no upstream fixes/manual answers were supplied. No full upstream suite ran.
The original owned GPT-OSS score remains **2/4**; the new context has not been
remeasured on those development cases.

Raw reports and failure audit: `evidence/revenue/groq-historical-v7/`.
Artifact `12384047110`, ZIP SHA-256
`1e42ebaa1c5caa5750f20c182cc78cab4dceab077f2c91117b62926441941bc6`.
The archive hash, report/replay binding, usage accounting and frozen source
hashes were checked locally without executing target source. The original
reports are unmodified. Syntax causes above were independently inspected with
AST parsing only. No extra live experiment was dispatched.

## Post-evaluation coordinator correction (not live-measured)

The 454 transcript revealed an orchestration bug: an earlier source-validated
sibling was classified as rejected when a different symbol failed. The retry
metadata now distinguishes `source_validated_partial` from `rejected_candidate`.
A validated partial proposal can recur while its sibling is revised; duplicate
rejected proposals still fail closed. A separate neutral two-function fixture
reproduces the orchestration sequence with mocked inference/tests. It supplies
no historical repair answer and is not counted as autonomous success.

This follow-up changes the current orchestration/context after the frozen
measurement; **1/5 is the frozen commit's score, not a newly measured score for
the follow-up**. The immutable freeze remains tied to c2d8f24. Further clean
quality assessment needs separate evaluation material rather than tuning and
rerunning this exposed set. Multiline-statement patching and output-shape
compliance remain measured weaknesses; validators/scope are preserved.

Local follow-up regression: **321 tests, 314 passed, seven skipped**; ten
historical harness tests passed. The seven skipped namespace/rootfs checks are
still unexecuted. Current Docker admission applies to owned/curated excerpts;
arbitrary customer code remains prohibited. No private production volume,
customer source, real order, sales deployment, repair schedule, external
submission or financial commitment. Confirmed received revenue remains **$0**.
