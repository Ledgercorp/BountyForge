# Phase 11 — frozen 20-case local Qwen evaluation

The Phase 8 frozen preparation/replay module remains provider-free. This phase
adds a separate, explicitly gated adapter to measure the existing frozen selection
with the already-pinned local Qwen model. It does not modify the task manifests,
source hashes, tests, selection digest, repair-session core, or historical
benchmarks.

The evaluation is accepted only on the GitHub-hosted `ubuntu-24.04` standard
X64 runner, for this repository and engineering branch. The gate is either a
manual dispatch with zero-cost confirmation or a push that changes only this
workflow file and carries `[qwen-frozen-eval]` in its commit message; the latter
supports a run without merging the workflow onto `main`. It refuses
known provider/payment/publication credentials and uses only the local
`127.0.0.1:8080` Qwen endpoint. The model and llama.cpp archive are SHA-256
pinned. There is no remote-provider fallback. A fresh 20-control Docker proof
must pass before the first model request. Each case is independently baseline
reproduced; the existing statement worker can make at most two calls per case
and forty calls in total. All generated changes remain one-source-path patches
subject to the frozen validators. A passing patch is counted only after the
existing independent worker verification and a fresh credential-free Docker
replay. Failed or unverified cases remain in the report with their actual
attempt details.

The workflow has no schedule, secrets, cache write, broader permissions or
production side effects. It only restores the existing public Qwen cache and
pulls the exact previously verified test image digest required by the ephemeral
runner. It uses the public standard hosted runner, no API inference, no new
infrastructure, and a one-day bounded evidence artifact. The manual
`confirm_zero_cost` input or explicit tagged workflow-only commit is a gate; it
cannot change the runner or inference backend.

## Current measurement

No new live inference result is recorded in this document yet. Do not treat
Phase 8 preparation (20/20 reproduced baselines, zero model calls), prior
historical Qwen studies, or the preauthored calibration fixtures as a Phase 11
score. The first admitted workflow must publish its run URL, commit SHA, report
artifact, per-case failure categories, actual request/token/runtime counts and
independent replay receipts here. If the runner or Docker preflight rejects,
the result is infrastructure-blocked and accuracy remains unmeasured.

Actual financial spend remains $0; local inference uses no model API. Customer
execution, private source, payments, delivery, external submissions and
production activation remain disabled.
