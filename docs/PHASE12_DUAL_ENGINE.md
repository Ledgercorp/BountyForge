# Phase 12 engineering contract

The active Codex session supplies bounded candidates over the native MCP client.
It does not start another Codex agent or call a paid inference API. QWEN_LOCAL
uses the existing numeric-loopback LocalModel with two calls maximum. The legacy
Qwen worker, protocols, frozen core and Phase11 evidence remain intact.

Both pathways prepare fixed public owned tasks and validate through the existing
AST statement, binding and source-capability validators. Fixed Docker test
commands use the existing pinned image and all twenty admission controls.
Successful candidates must pass a second fresh container replay. Receipts bind
the engine, task, original source, tests, proposal, candidate and observation
hashes. They grant no execution, payment, publication or delivery authority.

The owner selects Autonomous Qwen or Codex Agent in the terminal console, CLI
option, JSON configuration or MCP preparation call. CODEX_AGENT is a session
handoff, not a separately authenticated unattended provider. A missing session
does not initiate inference. No automatic provider fallback is implemented.

New Phase12 fixtures are development material, with no stored reference fixes.
MCP preparation returns permitted source and edit units, never verifier tests or
answers. The coding agent can still read this engineering repository, including
the fixtures it authored, so every result here is developmental. Independent
evaluation requires separately controlled tests outside the agent's filesystem
and a separate verifier identity. No caller flag can upgrade this admission.

Task capabilities and revision fences are process-local, expire after ten
minutes and allow at most two candidate submissions. Process restart invalidates
the capability; a new owned preparation is required. This is not durable
commercial job coordination. The existing commercial ledger is untouched.

## Operating the two engines

The local owner page is `dashboard/repair-console.html`. Open the file directly;
it has no server, network requests or deployment. Its selector downloads exactly
`{"engine":"CODEX_AGENT","case_id":"weighted-mix"}` (or the selected Qwen
mode and fixed owned case), consumed by `--config`. A Node process test exports
the page's real configuration and invokes the Python CLI with it. The page also
verifies real receipt SHA-256 bindings locally, rejects contradictory/tampered
outcomes, and labels signature/authorship authentication as unverified.

```
python -m scripts.repair_engine --list
python -m scripts.repair_engine --interactive
python -m scripts.repair_engine --config bountyforge-owned-engine.json
python -m scripts.repair_engine --engine QWEN_LOCAL --case-id sparse-average
```

CODEX_AGENT without a connected session returns `CODEX_SESSION_REQUIRED`, zero
additional model calls and no provider fallback. In an active Codex session use
`prepare_owned_repair(case_id, engine="CODEX_AGENT")`, then reason about the
returned source and public contract and call `submit_owned_repair(task_id,
revision, proposal)`. Proposals use the existing `changes:[{line,new}]` statement
protocol. The session can revise a failed candidate once. Every revision starts
from the pinned original. Task preparation does not reveal tests or answers.
`--session-stdin` provides the same explicit proposal handoff for a CLI client;
its selected mode is not proof of the submitter's identity.

`python -m scripts.codex_repair_session` is a bounded JSONL bridge through the
actual registered Codex app-server MCP client. It starts no `turn/start`,
`codex exec`, SDK model call or recursive coding agent. The current authenticated
engineering session supplies candidates between tool calls. Native registration
was reused; the bootstrap's stricter command-shape check refused its equivalent
existing entry. That entry was inspected as PATH-only and was not overwritten.
There is no new persistent Cloud MCP registration or remote host.

QWEN_LOCAL checks the existing pinned GGUF/runtime archive, running executable,
loopback process arguments and health before constructing LocalModel. The service
never downloads or starts a model, uses numeric loopback only, and makes at most
two bounded requests. Use the existing trusted Linux inference bootstrap to
prepare the runtime. The opt-in hosted Phase12 canary uses the public standard
Ubuntu runner and the existing public model cache, one owned task, two calls,
one inference stream and a one-day small artifact. It shares the global repair
worker concurrency group and has no recurring trigger or provider secret.

## Actual Codex development measurement

The active Codex session inspected these tasks through native MCP and generated
three new proposals with no reference fixes present. All passed the unchanged
source/statement/binding validators, all targeted tests and a second fresh
Docker run:

| Case | Candidate attempts | Targeted tests | Fresh replay tests | Outcome |
| --- | ---: | ---: | ---: | --- |
| sparse-average | 1 | 6 | 6 | AWAITING_OWNER_APPROVAL |
| label-order | 1 | 5 | 5 | AWAITING_OWNER_APPROVAL |
| weighted-mix | 1 | 6 | 6 | AWAITING_OWNER_APPROVAL |

This is **3/3 owned development repairs**, not independent accuracy or a revenue
claim. The same agent authored the fixtures and could inspect their tests.
Actual live trace: `evidence/phase12/codex_live_repairs.json`, SHA-256
`806e8762f130277ffdcb10e31c9f3a7a984fc85ea34cb9e95f77304f4b5a4aca`.
The MCP child exposed only PATH. Per-candidate active Codex token usage is not
available; it is recorded as null, not zero. The transport client started zero
additional agent turns and zero additional model-provider requests. No paid API
or extra infrastructure was used. Mode selection is recorded independently of
cryptographic authorship attestation, which remains false.

The separate credential-free replay process re-staged these exact raw proposals,
verified source/test/candidate/receipt bindings, ran a fresh 20-control admission
and passed another 17 test methods across the three candidates. Its full proof
is in `evidence/phase12/independent_replay.json`. This verifies recorded candidates;
it generates no new patches and makes no new accuracy claim.

```
python -m scripts.phase12_replay --evidence-sha256 806e8762f130277ffdcb10e31c9f3a7a984fc85ea34cb9e95f77304f4b5a4aca
```

The replay CLI requires a credential-free environment. Its fixed evidence input
and independently supplied hash fail closed on corruption before runtime
admission. Neither mode permits a caller-provided approval flag to activate
customer execution or delivery.

## Phase11 diagnosis and corrections

The three prior `model_or_runner_unavailable` records were reproduced without
new inference. The Phase11 adapter omitted `candidate=` when calling its owned
observer after a patch, so original-source custody rejected every changed copy
before Docker could run. This is an evaluator wiring defect. The adapter now
replays the exact captured response through both existing validators, compares
the resulting bytes to the worker copy, then passes that candidate binding to
the observer. Unbound bytes still fail. No frozen core or historical result was
rewritten, and no exposed benchmark inference was repeated.

Additional diagnostic Docker replay of the three already-recorded candidates
found actual repair defects: shipping_cartons failed five assertions;
running_measurements raised six test errors; wildcard_empty_prefix failed six
assertions and raised one error. The original end-to-end benchmark records stay
unchanged at zero verified repairs. The new diagnostic evidence is in
`evidence/phase12/phase11_worker_error_diagnostic.json`.

Most other Phase11 proposals violated the condition-expression/statement or
binding contract. The new shared path stages proposals before the additional
binding check, preserving precise rejection diagnostics rather than replacing
them with the generic binding error. It never coerces an invalid full `if`
statement into an expression. Identical proposals and equivalent failed AST
candidates do not execute twice. Sandbox admission, baseline observation,
targeted tests, independent replay and local inference failures have distinct
outcomes/stages. All existing source-capability restrictions remain in force.

## Black Box acceptance and operational limits

`evidence/phase12/blackbox_acceptance.json` records 14 real Codex MCP client
checks: wrong-logic rejection, stale revision refusal, bounded revision with a
fresh replay, completed-task refusal, arbitrary-path/customer-source/delivery
refusal, ineffective/capability patch rejection, attempt limits, engine
separation, unavailable-Qwen refusal without inference/fallback, PATH-only child
environment, and capability invalidation after a process restart. Its successful
revision reuses an already-recorded candidate and is excluded from the 3/3
development generation count.

One real integration defect was found: the inherited MCP PATH omitted
/usr/local/bin, making Docker unavailable. The first failure is preserved in
`codex_session_initial_admission_block.json`. Startup now clears all inherited
variables and installs only the trusted executable search path. New subprocess
regression coverage proves that arbitrary extra secret names are dropped.
The original five tool calls, five authorization refusals, controlled process
termination, reconnection and clean shutdown also passed native Codex client
acceptance with all ten tools discovered and zero model turns started.

The first full regression caught one stale bootstrap tool-count assertion;
it was changed to require the exact ten-tool inventory including the original
five. No security check was disabled. Current verification/commits and the
hosted Qwen canary outcome will be appended after CI finishes.

No private execution or commercial authority is established. Remaining gates
include actual unseen evaluation isolation, separately authorized unattended
Codex authentication if desired, Stripe TEST validation and approved commercial
terms/launch. Private execution separately lacks publisher/build/SBOM and
vulnerability assurance plus admitted private storage and per-job kernel/I/O
controls. All spending, payments, revenue and external submissions in this phase
remain $0/none; neither production nor recurring operation is activated.

## Official capability references inspected

On 2026-10-23, installed `codex-cli 0.163.0` and its `app-server --help`
were checked against the current official pages:

- https://developers.openai.com/codex/cli/
- https://developers.openai.com/codex/sdk/
- https://developers.openai.com/codex/app-server/
- https://developers.openai.com/codex/mcp/

The SDK can start additional threads/model turns; no SDK dependency or separate
authentication was introduced here. The native app-server MCP tool-call path is
used solely as transport for the already-active session. Cloud MCP persistence
and an unattended Codex model backend are not inferred from CLI configuration.

Local final implementation checks: 636 Python tests ran, 627 passed, nine
existing skips, zero failures; historical harness 10/10; dashboard/console Node
tests 6/6. Actual legacy native Codex-client acceptance retained all five valid
tool calls and five refusals, with controlled termination/reconnection and a
PATH-only child. Current controlled Docker admission still passes all 20 checks;
the existing skipped namespace/rootfs suite remains separately unverified.
