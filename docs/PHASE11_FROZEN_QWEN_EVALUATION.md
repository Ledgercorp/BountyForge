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

## First measurement segment

At commit `777004ca60f0b3252c97112e851f22c89944f273`, hosted run
[39896337388](https://github.com/Ledgercorp/BountyForge/actions/runs/39896337388)
passed its full 610-test regression gate, restored the existing public model
cache, verified both pinned model/runtime digests, pulled the previously
verified Docker image, and passed all 20 fresh Docker controls before inference.
The bounded report is retained as
[`partial_qwen_39896337388.json`](../evidence/phase11/partial_qwen_39896337388.json)
with SHA-256 `b3bd0415afbc3a910e3de797e819c7f5c6a7b2cc190894b823b25811007d47c7`.

The first segment made **11 local Qwen calls** across six cases: **9,204 prompt
tokens, 693 completion tokens, 65.541 seconds in inference, 81.147 seconds in
the evaluation coordinator**, and $0 model/API cost. Four cases received two
proposals each that the unchanged source/AST validator rejected because the
model returned complete `if` statements where condition edit units require
only an expression (eight rejected responses). `line_termination` received two
semantically ineffective proposals. `shipping_cartons` produced one candidate,
then the worker reported `model_or_runner_unavailable` before recording a test
receipt. Five model cases therefore yielded no admitted patch; one was blocked
at the worker/test boundary. No case was accepted and independently replayed;
the full-suite `accuracy` remains **null**, not 0/20.

After the run stopped, a separate diagnostic replay of the exact recorded
`shipping_cartons` response passed a fresh 20-control Docker admission and ran
eight fixture tests. The candidate failed five targeted assertions. This
post-run diagnostic is recorded in
[`shipping_cartons_postrun_diagnostic.json`](../evidence/phase11/shipping_cartons_postrun_diagnostic.json);
it is not an end-to-end worker success and is excluded from the success count.
The initial worker error is only recorded as the generic
`model_or_runner_unavailable`, so its exact transient cause remains unknown.

## Second measurement segment

At commit `4df5b182cce04d8fb68b5a3bcd3b4f0e58d70f13`, hosted run
[39934425118](https://github.com/Ledgercorp/BountyForge/actions/runs/39934425118)
passed evaluator admission tests, restored the public cache, verified the
pinned model and runtime, and again passed the 20-control Docker proof. Its
SHA-pinned report is
[`partial_qwen_39934425118.json`](../evidence/phase11/partial_qwen_39934425118.json)
with SHA-256 `d217280a31a7dabd6e8bb03b9e64a588d7daa9abaf678a2a88b5442e7d01e47d`.
It made **three additional local model calls** across the two new cases
`block_indentation` and `running_measurements`; the accumulated total is 14
calls over eight attempted cases. No patch was accepted or independently
replayed. Twelve cases remain untouched. Full-suite accuracy remains **null**.

`block_indentation` received two rejected proposals. Both replaced three
required-binding statements with whitespace-only text, and the unchanged
binding/source validator rejected them. `running_measurements` returned a
single plausible but incomplete proposal; the worker stopped with the generic
`model_or_runner_unavailable` error before a candidate test receipt existed.
The exact cause of that worker error is not available in the report, so this
case is blocked/unverified, not a targeted-test failure. The report records
101.609 seconds summed across all model-call timers to date and 46.622 seconds
for this segment's coordinator wall time. These fields cover different scopes;
the raw `elapsed_seconds` field is per segment while `inference_seconds` is
cumulative.

## Third measurement segment

At commit `c328532d597e2af0dc5464d3d757a602f24f76bd`, hosted run
[39935203508](https://github.com/Ledgercorp/BountyForge/actions/runs/39935203508)
again passed the test gate, pinned model/runtime verification and all 20 Docker
controls. Its report is
[`partial_qwen_39935203508.json`](../evidence/phase11/partial_qwen_39935203508.json)
with SHA-256 `b2621e12fb2118534ba7b67b9cdc1dcbca32594d0b7fd13f8bedc4f86186433c`.
It dispatched 11 previously untouched cases, using 21 calls. The cumulative
total is **35 calls, 34,215 prompt tokens and 2,445 completion tokens**. It
records 218.014 seconds cumulative across model-call timers and 131.584
seconds for this segment's coordinator wall time. The report's model-call
timer is cumulative while coordinator wall time is per segment.

The aggregate has 19 cases attempted, zero accepted patches, zero targeted
test executions of a model candidate, and zero independent replays. Thirteen
cases were routed to source/patch validation rejection across the suite, two
to ineffective proposals, one to other patch validation, and three to the
generic inference/test-runner failure category. These category counts sum to
19. Most model proposals failed the existing required-binding/source
validator; no validator or Docker rule was loosened. Three cases stopped at
`model_or_runner_unavailable` before a candidate test receipt. Accuracy for
the full 20-case suite remains **null** because `network_word_order` has not
yet been dispatched. It is accurate to say zero independently verified
repairs among the 19 attempted cases; this is not a completed 0/20 score.

## Final measurement segment

At commit `11ed760dc145d09a38d333246a115d304734ebc9`, hosted run
[39935810157](https://github.com/Ledgercorp/BountyForge/actions/runs/39935810157)
passed regression admission, model/runtime hash verification and all 20 fresh
Docker controls. It attempted only the final untouched case,
`network_word_order`, making two calls. The exact final report is
[`final_qwen_39935810157.json`](../evidence/phase11/final_qwen_39935810157.json)
with SHA-256 `45781c9e2bf691faadbe3673e263000b37d9275220c4104ae9f75178be1a0d47`.

The frozen 20-case selection is now complete: **20 cases attempted, 37 local
Qwen calls, 36,134 prompt tokens, 2,615 completion tokens, zero accepted
patches and zero independently replayed repairs**. Recorded model-call time
is 234.626 seconds. The four segment coordinator times in their respective
raw reports sum to 289.441 seconds. Inference is local, model/API cost is $0,
and no credentials or remote fallback were available to the process.

The final classification is 14 source/patch validation rejections, two
ineffective proposals, one other patch validation rejection, and three generic
inference/test-runner failures. No candidate patch reached an independently
verified passing state. Thus the frozen set result is **0 independently
verified repairs / 20 attempted**, with the three generic worker failures
retained as unverified rather than attributed to model correctness. The
workflow completed, but the recorded model repair performance is not suitable
for commercial work.

The raw final JSON also retains a stale `blocking_reason` from a prior partial
segment even though its status is `completed` and all 20 cases are present.
This is an evidence aggregation defect, not a run failure. The coordinator now
clears inherited blockers on completion and records elapsed time per segment;
a unit regression covers both. The preserved raw report has not been edited.

This fixed catalog and all its responses are now exposed; no more model calls
should be spent on it. Prompt or repair-engine changes require a new unseen
evaluation set for an independent accuracy claim.

Actual financial spend remains $0; local inference uses no model API. Customer
execution, private source, payments, delivery, external submissions and
production activation remain disabled.
