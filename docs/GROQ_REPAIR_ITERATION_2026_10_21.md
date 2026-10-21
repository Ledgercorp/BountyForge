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
