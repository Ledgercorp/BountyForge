# Next-generation owned model evaluation

Engineering branch `engineering/revenue-linux-scout-20261021`; baseline checkpoint
`0f31fc3825f64073be058513358a5f4709283e16`. Neither draft PR is merged.

## Frozen design before inference

Three new LeftSock-owned maintenance tasks exercise event checkpoint/deduplication,
interval compaction with helper dependencies, and bounded HTTP retry recovery.
Each defines eight regression methods and two interacting faulty statements.
There are no reference patches. All three reproduce assertion failures through
the existing twenty-control Docker admission. Before freezing, the new test
filenames were changed to the existing verifier's required `test_regression.py`;
no assertion was changed. Source/tests and experiment implementation are hashed.

This is **developmental evaluation**, not unseen accuracy. The active agent can
read this repository's tests and edit its workflows. No independently controlled
held-out store inaccessible under that authority exists. Not including tests in
the prompt does not create that boundary. Docker replay independently checks a
model candidate; it does not make these problems unseen.

Three local profiles are compared: existing default QWEN_1_5B, experimental
QWEN35_4B and GRANITE42_3B. QWEN_LOCAL remains the existing engine identifier;
the explicit model profile/digest identifies the actual local patch generator,
including IBM's model. CODEX_AGENT remains a separate session-driven author.
No Codex-authored candidate, reference solution or provider fallback is used.

The named **NEXTGEN_TRIAL** envelope explicitly changes the generation budget:
four threads, one stream, 2,048 context, <=1,200 rendered input tokens, <=256
output tokens, 75s/request, two attempts/task, <=600 aggregate process CPU seconds,
240s process wall limit, 10GiB address space, 1MiB log, no core files. Load deadline
remains 60s. Legacy defaults remain 45s/150 tokens/180 CPU seconds and 180s wall.
Both new and baseline models receive identical limits in this experiment.
There are at most 18 completion requests and no extra calibration inference.
Every request records tokenizer usage/returned token counts where available;
unreturned usage stays unknown. Each task gets a fresh bounded model process.

The existing owned queue reserves attempts durably, preserves exact profile
identity and fences results. A fixed heartbeat renews the lease during slower
inference without extending the existing job deadline or attempt budget. Public
standard `ubuntu-24.04` runners only; manual dispatch requires an explicit true
no-charge input and public repository/branch gates. Credentials are removed from
the controller, model and Docker execution. Small artifacts live one day; no
new-model cache writes; experimental weights are removed in an always step.

## Model provenance and compatibility

See `evidence/nextgen/upstream.json` and `bountyforge/model_profiles.py` for exact
revisions, LFS SHA-256 declarations, file sizes and source-document hashes.
Official Qwen3.5-4B and IBM Granite 4.2-3B cards declare Apache-2.0. Qwen's actual
LICENSE was read and hashed. IBM publishes its GGUF directly; the Qwen artifact
is Unsloth's quantization with a declared official base. Its conversion input
revision and build are not independently attested. Observing an official source
revision today does not prove it was the quantizer's input. Neither model has
authenticated conversion provenance established here. Full GGUF digest checking
is mandatory before launch; upstream metadata alone is not a local hash check.
These limitations preclude stronger provenance/private-execution claims.

The runtime remains **llama.cpp b11750**, archive digest unchanged. Its tag
resolves to `dd002b91f583af0b80140f9a140dc04856bfc2e0`; read-only source inspection
found Qwen3.5 architecture, Qwen3.5 tokenizer and Granite architecture support.
The runtime's apply-template parser accepts `chat_template_kwargs.enable_thinking`.
Both newer models default to thinking, so the bounded JSON experiment explicitly
requests non-thinking mode and refuses an unclosed thinking prefix. It never
closes tags manually, strips model output or installs a different tokenizer.
Actual load, model props and tokenization must still pass on the downloaded GGUF.

Qwen3.5-9B Q4_K_M is 5,680,522,464 bytes. It is deferred until smaller models
demonstrate practical resource use: Phase15's 7B exhausted its CPU envelope.
No 9B weight download or inference is performed merely to enlarge the candidate list.

## Architecture choices

Read-only inspection of pinned mini-SWE-agent configuration confirmed its
action/observation iteration and truncation feedback pattern. BountyForge keeps
its own two-attempt, validated-edit loop and exact test feedback. It does **not**
adopt mini-SWE-agent's general shell actions. No upstream code was executed.

Aider's repository map uses token budgets and ranked relationships. This trial
uses a small stdlib AST dependency map: target plus at most five transitive helper
symbols, depth two, line ranges and call edges. Helpers remain read-only. The
full authorized source is retained; no extra files, imports or commands become
available. Retry feedback distinguishes repeated candidates, source rejection
and actual regression failure. This is an independently implemented pattern,
not a port of Aider's execution or provider stack.

ast-grep and Ruff release metadata were inspected. Neither is installed/activated.
For the current fixed single-file statement scope, Python AST already provides
structural anchors and capability/binding checks. A new structural tool does not
resolve incorrect repair logic. Ruff could add static diagnostics later, but it
would require a separately pinned executable/admission contract; formatting fixes
and automatic scope expansion are not admitted. This keeps the model comparison
focused. No measured superiority over the old architecture is claimed: every
model in this trial uses the same new prompt/grammar, not a separate randomized
architecture arm.

## Confirmed engineering fixes and preflight

New-profile tests reproduced a hardcoded queue forwarding rule that only passed
QWEN_7B explicitly, defaulting other choices to 1.5B. The regression test failed
before the smallest fix: forward every explicitly selected local profile. Profile
and SHA receipts, SQLite restart constraints, optional MCP enums and the local
owner selector remain consistent. Unknown profiles fail closed. New profiles
do not replace the default. No new MCP tools or network listener are added.

The old Phase15 raw receipts and frozen configuration bytes remain unchanged and
are still verifiable. Its unmeasured V5 configuration is superseded by this new
frozen experiment; implementation hash checks prohibit running old configs on
changed code. Phase15 results remain zero verified repairs, not a 7B 0/3 score.

Live outcomes are pending at this freeze. Offline unit tests do not establish
repair accuracy. Final evidence and measurements will be appended after actual
execution. Customer execution stays NOT_ADMITTED, commercial authorization false,
main unchanged, production inactive, spending and confirmed revenue $0.

Pre-dispatch regression: 725 tests, 716 passed, nine existing skips, no failures;
Node 8/8. Actual Codex app-server MCP discovery retained all 18 tools, original
five successful calls, five refusals and kill/reconnection, PATH-only child,
zero model turns/inference. New profile/queue and unavailable-backend tests pass.

GitHub did not register the newly added manual-only workflow on this feature
branch (workflow lookup returned HTTP 404). Main is not changed to register it.
The comparison instead reuses the already registered Phase15 manual workflow
entry point; the superseded, never-measured V5 launcher's exact bytes are
archived under `experiments/phase15/unmeasured-v5-workflow.yml`. No push trigger
or automatic inference is added. All earlier workflow run records remain intact.

Sampling caveat, recorded while the trial is still running: the frozen native
transport uses temperature zero for every model, preserving the deterministic
baseline decoder. IBM's card recommends temperature 1.0 and top_p 0.95 even in
non-thinking mode. Shared greedy decoding is a controlled protocol comparison,
not an optimized-model comparison. Neither a failure nor a success establishes
the model's performance under its recommended sampler. A future sampling arm
would require a separately frozen experiment and fresh tasks, not retuning these
three problems and claiming unseen accuracy.

## First actual trial and controller correction

Implementation commits `cf168148c245246bc71a941274964d1c8ee9ec7c` and
`a53bd6a95f9f1ec5ab75f7da93f5f5a70bda7be4` passed hosted regression
[40021185351](https://github.com/Ledgercorp/BountyForge/actions/runs/40021185351):
725 tests, 716 passed, nine existing skips, Node 8/8.

[Trial 40021191461](https://github.com/Ledgercorp/BountyForge/actions/runs/40021191461)
ran for 434.618s and ended PARTIAL_BLOCKED. Actual full model/runtime hashes,
loaded model identity, non-thinking rendered templates and tokenization passed.
All seven model processes stopped normally; no CPU/wall/memory cap was exceeded.

| Model | Completed tasks | Valid patches | Verified repairs | Calls | Returned prompt/output tokens | Inference seconds | Peak RSS KiB |
|---|---:|---:|---:|---:|---|---:|---:|
| Qwen2.5 Coder 1.5B | 3 | 3 | 0 | 6 | 3640 / 354 | 62.397 | 1946168 |
| Qwen3.5 4B | 3 | 0 | 0 | 6 | 3837 / 625 | 221.706 | 4757604 |
| Granite 4.2 3B | 1 | 2 | 0 | 2 | 1352 / 145 | 57.283 | 4081128 |

Granite's other two cases were not attempted; this is not a 0/3 score. All
returned responses are genuine local model output. No repair passed a targeted
suite or independent successful-repair replay. Source-valid proposals introduced
new failures; the machine summary lists exact new failing test IDs per attempt.

1.5B misunderstood state accumulation, repeated rejected/failed candidates, and
rewrote the retry guard incorrectly. Qwen3.5 returned Python headers/fragments at
wrong statement anchors, invalid condition expressions, repeated a malformed
statement and once exhausted 256 output tokens before completing JSON. Its five
other responses used <=131 tokens: merely raising the output cap did not solve
its contract misunderstanding. Granite inverted an eligibility guard and retained
faulty state logic; its second proposal introduced another regression. None of
these outcomes justify replacing the default. The larger CPU envelope allowed
both newer models to return proposals without timeout; it did not establish
useful repair quality.

A real controller race stopped Granite after its completed first task. The
heartbeat renewed at 30s, then attempted renewal after `_finish` had atomically
committed FAILED and deliberately cleared the lease. The refusal is correct;
the controller incorrectly called it WORKER_BLOCKED. The raw artifact is intact.
A failing regression plus a separate-SQLite-connection reproduction verifies the
fix: stop heartbeat before runtime shutdown, and distinguish a committed terminal
result from in-flight revocation. Expired/stopped leases remain rejected by the
unchanged queue fence. No result or model failure is reclassified as success.

Only Granite's two unattempted tasks are prepared for continuation, with unchanged
model, sampler, prompt, source/tests, validator and generation envelope. Its four
maximum requests plus the original fourteen stay within the original eighteen.
The continuation config binds the exact prior artifact and verifies that those
tasks were not attempted. It downloads only Granite and the same runtime, not
Qwen again. Full-run config and receipts remain immutable. Current continuation
regression: 727 tests, 718 passed, nine skipped, zero failures.

Separate credential-free Docker replay revalidated all five source-valid failed
candidates (40 methods) and reproduced every failed suite. No model was running
and no new inference occurred. The first launcher invocation could not resolve
`python` in its cleared PATH and executed no tests; selecting the existing
absolute interpreter corrected it. Replay evidence records zero successes.

The default remains QWEN_1_5B. No model has demonstrated commercial readiness.
Qwen3.5-9B remains unmeasured/deferred: the smaller model's dominant failure was
patch-contract adherence, so another large download is not justified yet.

## Completed Granite continuation and final comparison

Continuation [40023194501](https://github.com/Ledgercorp/BountyForge/actions/runs/40023194501)
on `e578de96cff642a53d4b676bf8aed87955519876` completed the two unattempted tasks
in 156.852s without heartbeat failure, cap exhaustion or unexpected server exit.
Four real completion requests returned 2641 prompt
and 509 output tokens. One candidate was
source-valid but failed tests; repeated/invalid proposals remained rejected.
Fresh credential-free replay reproduced that failed suite; zero successes.
No model, prompt, task, test, validator, sampler or resource envelope changed.
The original fourteen requests plus these four equal the frozen eighteen maximum.

Final developmental scores: **Qwen2.5 Coder 1.5B 0/3, Qwen3.5 4B 0/3, IBM Granite
4.2 3B 0/3**. Each model made six real requests. No new model demonstrates better
verified repair ability under this protocol. Granite's invalid interval edit
contained a whole block at an assignment anchor; its retry repeated it. Its retry
policy edit used a truthy tuple for a condition and failed regression, then
repeated the candidate. The exact raw calls and all rejected/failed outcomes are
preserved; no manual correction entered a model result.

Total new trial spending and confirmed revenue $0. Existing default, production,
schedules and commercial/private admission are unchanged. All previous phase
artifacts are intact. Hosted continuation regression
[40023174946](https://github.com/Ledgercorp/BountyForge/actions/runs/40023174946)
passed 727 tests (718 passed, nine existing skips), plus Node 8/8. These outcomes
are preserved before continuing the separate Phase18 native-runtime investigation.
