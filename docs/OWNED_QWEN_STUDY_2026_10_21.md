# BountyForge owned structural model study, 2026-10-21

## Actual independent GitHub-hosted Linux run

- Workflow: [39634493066](https://github.com/Ledgercorp/BountyForge/actions/runs/39634493066)
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

1. Compare opt-in GPT-OSS 120B via Groq Free Plan on the **same frozen owned
   structural tasks** plus the unchanged independent Boltons set, under
   explicit token and total-call limits. Inference has not yet run because
   no private key/current free-plan attestation is configured.
2. Benchmark blind: no examples of fixture solutions fed to the model; keep
   deterministic source SHA and test results.
3. Evaluate both pass rate and correctness-reject evidence: model-produced
   syntax-invalid proposals, new execution capability, no-op edits,
   repeated ineffective patches, actual regression test success and
   per-task token/call budget.
4. A model completing even 4/4 owned tasks alone is not enough for customer
   work: the existing seven rootfs namespace tests remain skipped, and
   arbitrary third-party dependency/source admission is unverified.
5. A paid service pilot stays blocked pending admitted private customer
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

Owner-facing result: these measurements justify seeking a stronger coding
model, not automatically selling fixes.
