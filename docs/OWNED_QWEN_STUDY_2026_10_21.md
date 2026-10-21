# BountyForge owned structural model study, 2026-10-21

## Actual independent GitHub-hosted Linux run

- Workflow: [39634493066](https://github.com/Ledgercorp/BountyForge/actions/runs/39634493066)
- Canonical study head: `1c0fe8faea4ff45be63cecc9e527e693f69fd0c9`.
  PR workflows may record a separate generated merge revision in their artifacts.
- Immutable Python Docker admission and pinned SHA-256 Qwen2.5-Coder-1.5B
  GGUF / llama.cpp runtime verified in workflow.
- Four structural **owned** fixture tests were individually reproduced as
  failing before generation. No commercial source, outside submission,
  remote model API, Mac or new spending.
- Phase 4 harness 10/10 passed.
- v5 `ast_contract_v5`: **0/4 verified fixes, eight model calls**.
- v6 `ast_contract_v6`: **0/4 verified fixes, sixteen model calls**.
- This is a small owned-study result, not an accuracy estimate across industry
  code. Historic independently sourced Boltons v5 remained 0/5. Synthetic
  fixture success must not be promoted as actual paid work.

## Specific failure analysis from retained GitHub artifact

Fixture | v5 behavior | v6 behavior
--- | --- | ---
optional_banner | Repeated identical patch; regression tests still failed | Correctly noticed None concatenation, but proposed an ineffective two-line patch; regression tests still failed
reference_code | Edits produced Python syntax errors | Proposed newly introduced attribute/call capabilities, which the source-security validator rejected
setting_precedence | Repeated wrong dictionary-merge ordering | Changes were ineffectual or became no-ops on retry
empty_summary | Repeated inadequate assignment | Diagnosis selected a candidate line but patch did not meet regression tests

These are measurable weaknesses of the current model/prompt/proposal
interaction, not a signal that tests or safety checks should be relaxed.
Especially, do **not** disable AST capability restrictions to improve a
headline pass rate.

## Next model acceptance gate

1. The gated Groq canary defaults to the **same frozen owned structural tasks**
   using v5, with an optional explicit selection of the earlier original owned
   set. Both modes retain eight calls and the unchanged validators. A complete
   v6 study would need a separately reviewed sixteen-call budget; it is not
   implemented by this canary. Groq inference has not been run by this work.
   Current Free Plan status, credential setup and applicable authorization remain
   prerequisites, not results of this study.
2. Sending historical Boltons excerpts to a remote model is outside the current
   owned-only canary. That route requires a separate source-transmission and
   execution review before implementation or invocation. The fixed Boltons set
   and its existing local-model path remain unchanged.
3. Benchmark blind: no examples of fixture solutions fed to the model; keep
   deterministic source SHA and test results.
4. Evaluate both pass rate and correctness-reject evidence: model-produced
   syntax-invalid proposals, new execution capability, no-op edits,
   repeated ineffective patches, actual regression test success and
   per-task token/call budget.
5. A model completing even 4/4 owned tasks alone is not enough for customer
   work: the existing seven rootfs namespace tests remain skipped, and
   arbitrary third-party dependency/source admission is unverified.
6. A paid service pilot stays blocked pending admitted private customer
   workspace, owner-approved terms, trusted payment proof, payout/refund
   obligations and held-out coding results.

## Workflow discipline

The Qwen study was initially triggered on PR events in order to get the
feature-branch workflow admitted. That unintentionally requeued the same
benchmark whenever the PR changed. After the first actual result, the study
was converted to an explicit manual-only `workflow_dispatch` path
(`run_owned=true`), eliminating additional automatic model evaluations.
Any already-running older snapshot could finish, but no recurring schedule
was authorized.

The read-only follow-up audit found the following actual executions; they are
separate experiments, not extra repairs added to the canonical score:

| Run | Head source | v5 | v6 |
| --- | --- | --- | --- |
| [39634357685](https://github.com/Ledgercorp/BountyForge/actions/runs/39634357685) | `d281af4940bdc111ff98bb82d19bf0aa744256e3` | 0/4, eight calls | 0/4, sixteen calls |
| [39634493066](https://github.com/Ledgercorp/BountyForge/actions/runs/39634493066) | `1c0fe8faea4ff45be63cecc9e527e693f69fd0c9` | 0/4, eight calls | 0/4, sixteen calls |
| [39634932291](https://github.com/Ledgercorp/BountyForge/actions/runs/39634932291) | `bcdb08fdd17415afbba3eb71c305a91378d1fc86` | 0/4, eight calls | Blocked before inference, zero calls |

The last run's v6 artifact reports `sandbox_admission_failed` with message
`Container cleanup unavailable`, at generated merge revision
`d857911bc1d7220dccf06c5204096afea2938a25`. This is an infrastructure/security
admission failure, not a 0/4 model result. Artifact `12360792980` SHA-256 is
`f1a74ecbdef49b99b9670a387c91e5407c606c4a61408593a5c93e269de4f1ae`.
No safety check was bypassed and this audit did not rerun the study.

These three inspected runs establish at least 56 actual model calls. Older
cancelled runs may contain additional partial calls; they have not been counted
as zero or silently included in the canonical experiment. Workflow artifacts
have one-day retention, so links alone are not a durable transcript archive.

Both new inference workflows now share the existing `bountyforge-repair-worker`
concurrency group, preventing them from running alongside another repair/model
worker. No recurring model schedule is present. Revenue scout push/PR checks
are offline; live research is manual-only and its proposed cron was removed.

Owner-facing result: these measurements justify seeking a stronger coding
model, not automatically selling fixes.
