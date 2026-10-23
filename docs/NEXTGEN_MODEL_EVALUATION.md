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
