# Phase13 — bounded owned queue and evaluation honesty

Checkpoint: `dd7b3e4bf7878b280a76d7928e6a33ebd72c1ce2`.
Branch: `engineering/revenue-linux-scout-20261021`. Both PRs remain draft.

The existing dual-engine service, receipt format, owner console and validators
are preserved. The new `owned_repair_queue.py` wraps that service; it cannot
accept source, paths, commands, test code, credentials or completion flags.
Only six hash-pinned owned development identities are admitted. The old Phase12
manifest and the frozen Phase8/11 material remain unchanged.

## What runs autonomously

An active authenticated Codex session can create an explicit batch, claim tasks,
reason about the returned source, submit proposals, read actual verification
feedback, revise within budget, and select the next task without user input.
The session performed that cycle for three newly authored development defects:

| Case | Generated proposals | Targeted tests | Fresh replay tests | Result |
| --- | ---: | ---: | ---: | --- |
| chunk-count | 1 | 6 | 6 | VERIFIED, awaiting owner approval |
| optional-setting | 1 | 6 | 6 | VERIFIED, awaiting owner approval |
| inclusive-window | 1 | 6 | 6 | VERIFIED, awaiting owner approval |

The active Codex agent generated these candidates, rather than invoking Qwen or
loading reference implementations. There are no stored reference fixes in this
catalog. This is **3/3 developmental repairs**, not unseen accuracy. This agent
authored the fixtures and can read their tests. Per-proposal Codex tokens are
unavailable (`null`); the MCP transport started zero additional model turns and
provider requests. The session bridge took 225.990 seconds including reasoning
and tool intervals, not pure inference time. Additional spending: $0.

`evidence/phase13/codex_queue_session.json` is the actual native Codex MCP trace,
SHA-256 `42a7be644b2f566276f1205959aa25600f5a26bc23e69f440ba3210d68f5b488`.
Each candidate passed the unchanged statement/binding/capability checks, then
targeted tests and a second fresh Docker observation. A further credential-free
process re-staged all three exact proposals and passed another 18 test methods
after fresh twenty-control admission. `independent_replay.json` records that
replay, not independent unseen model accuracy.

## Coordination and recovery contract

The fixed gitignored `.bountyforge-owned-queue/state.sqlite3` has owner-only
directory/file permissions, regular-file/symlink/hardlink checks, bounded size,
SQLite immediate transactions and synchronous durable writes. It stores owned
engineering data only, separately from all commercial ledgers. It is durable
across local process restarts; it is **not proven durable across Cloud workspace
replacement**, and is not scheduled production coordination.

Hard limits: four batches per store, five distinct fixed tasks per batch, one
active worker globally across engines, two claims per job, two reserved proposal
attempts per job, three-minute leases, ten-minute absolute job deadlines and a
thirty-minute window for starting work in a batch. There is no automatic store
reset, budget reset, recurring trigger or external publication step.

Each proposal reserves budget before execution. A crash consumes that reservation
even if no result was committed. Qwen reserves its two-call maximum before
starting; actual inference calls remain separately reported and can be zero if
the runtime is unavailable. Heartbeats cannot extend the absolute deadline.
Recovery requires a new lease, fresh admission and baseline reproduction; it
never resurrects a process-local task capability or promotes an interrupted
candidate. Exact proposal hashes survive restart to reject repeated work. A
still-active but disconnected lease can be explicitly released using its token;
otherwise it expires. Stale writers cannot update a recovered job.

Stopping is irreversible for a batch, revokes current leases and blocks new
claims/submissions. Already-started bounded Docker work may finish; its result
cannot commit success after revocation. This is a coordinator stop, not a claim
that kernel work is instantly killed. The separate CLI works while MCP is busy:

```
python -m scripts.owned_queue create --batch-id example --engine CODEX_AGENT --case-id chunk-count
python -m scripts.owned_queue status --batch-id example
python -m scripts.owned_queue stop --batch-id example
```

Use the eight queue MCP tools for session-driven Codex. Use `run-qwen` on an
explicit QWEN_LOCAL batch for the standalone bounded local engine. Neither
selection silently changes providers. A Codex batch cannot use that CLI to
launch another Codex turn. The existing engine selector and five original MCP
tools retain compatibility; native discovery now requires the exact 18 tools.

Queue terminal success additionally checks receipt, source/test/proposal/candidate
and runtime-admission hash bindings, both passing observations and denial flags.
Status refuses a corrupted cached success. These are integrity checks, not
signatures against an adversarial actor with the coordinator's filesystem UID.
Unexpected worker exceptions become sanitized WORKER_ERROR/BLOCKED outcomes;
admission, baseline and engine-unavailable failures remain distinguishable.

## Qwen contract diagnosis and experiment

Phase12's real Qwen response replaced a statement with the entire function. The
validator correctly rejected it; the identical retry performed no tests. The
new generation adapter uses one JSON-schema alternative per trusted AST anchor,
single-line replacements, exact assignment bindings and return prefixes where
applicable. It never extracts a patch from a rejected full function and does not
weaken the underlying validator. Unsupported or incorrect model output remains
rejectable. The original Qwen client and frozen evaluation pathway remain intact.

The opt-in Phase13 public standard-Ubuntu canary compares the legacy and new
schema on **one new owned development fixture**, with at most four model calls
total, no credentials, the same pinned assets and verifier, one inference stream,
the existing worker concurrency group and a small one-day artifact. There is no
paid fallback or automatic historical benchmark rerun. Live measurement is
reported separately when evidence is available; an offline schema test alone
does not establish improved model repair accuracy.

Actual hosted result at implementation commit
`2b0272df2975994eddff59d788a93b32c7fbadbd`:
[Qwen comparison 39947581082](https://github.com/Ledgercorp/BountyForge/actions/runs/39947581082).
Both protocols repaired `optional-setting` on their first call with the same
model-generated patch. Each passed six targeted tests and six fresh replay
tests; neither produced a rejected proposal or unauthorized change. This is one
development case measured twice, **1/1 per protocol**, not two independent tasks
or evidence of an accuracy improvement.

| Protocol | Calls | Prompt tokens | Completion tokens | Model seconds | Cycle seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| legacy_line_schema | 1 | 322 | 41 | 6.518 | 7.299 |
| qwen_statement_schema_v2 | 1 | 370 | 41 | 7.197 | 7.977 |

Total: two calls (four allowed), 692 prompt and 82 completion tokens, 13.715
seconds in inference, 33.686 seconds including both admission/preparation cycles,
55 seconds for the whole standard public Ubuntu job. No paid provider or model
credentials were used. Model/runtime/image pins are the existing Phase12 pins.
Exact artifact: `evidence/phase13/qwen_contract_39947581082.json`, SHA-256
`73eaeabbfc8de3777e594aa1e661be448ddb3a799da7fae8f219459422f960df`.
The real Qwen receipts also pass the same queue integrity checker as Codex's.
Successful available-runtime Qwen inference was measured through RepairService;
native Qwen queue acceptance measured the unavailable-runtime refusal. A live
successful Qwen queue job has not separately been measured.

The v2 generation adapter deliberately offers a one-physical-line subset of the
existing statement protocol. Codex's multiline interface and the original Qwen
client remain intact. The small comparison provides no evidence of improved
repair accuracy or lower inference cost; v2 used 48 more prompt tokens here.
Phase11's exposed 0/20 and Phase12's failed canary remain unchanged.

## Acceptance and unseen evaluation

The native Codex MCP Black Box run passed 22 checks: exact tool discovery,
PATH-only environment, idempotency, strict input refusal, single active worker,
heartbeat, failed regression, stale revision, source-capability rejection,
attempt exhaustion, controlled MCP kill, durable restart state, lost-capability
refusal, fresh recovery, stale-writer fencing, fresh independent verification,
separate-process stop, permanent stop, engine fencing and unavailable Qwen
without inference/fallback. It reused already-recorded candidates, generated no
new patches and contributes nothing to the 3/3 generation count.

Additional deterministic tests cover lease expiration, crash reservations,
simultaneous claims, bounded recovery, stop during verification, corrupted
receipts, worker errors and private-file checks. These tests use explicitly fake
observations and are not model or Docker evidence. After receipt hardening, a
new actual Codex MCP process validated all three durable successful records;
see `restart_status.json`.

`unseen_evaluation.py` prepares a strict hash-bound public-only handoff and
rejects test/answer/admission fields. It cannot admit unseen evaluation. Actual
environment investigation found no separately controlled verifier host or
identity inaccessible to this coding agent. Mode-000 local files can be made
readable again by their owner. Hiding tests from MCP or moving them within this
checkout is insufficient. A separate controller must freeze tasks and secret
tests, restrict the coding agent's filesystem/tools/network access to answers,
bind the generation transcript and candidate, and return authenticated replay
evidence. Until that boundary exists, every reported repair is developmental.

Official Codex app-server, SDK and MCP documentation and installed 0.163.0 were
checked. Read-only account metadata reports ChatGPT authentication, unknown plan
and unavailable rate-limit data (RPC -32603). No separate zero-cost unattended
backend, persistent Cloud session or verified quota follows from that. No
`turn/start`, recursive Codex, SDK inference or paid API was invoked.

Private execution remains NOT_ADMITTED. No customers, Stripe operations,
deliveries, production deployment, public service activation or upstream
submission occurred. Revenue and additional spending remain $0. The next
commercial-quality milestone is an externally controlled unseen owned evaluation
plus verified free inference availability, followed by owner review of the
existing inactive patch-only service. Runtime/private-storage/consent and
commercial launch gates remain separate and unresolved.

Local implementation acceptance: 659 Python tests executed, 650 passed, nine
existing isolation skips and zero failures. The historical benchmark harness
passed 10/10 model-free tests; the owner-console/dashboard Node suite passed
7/7. Frozen core pins and evaluation files remain unchanged. The skipped
namespace/rootfs checks were not completed by Docker admission. Structured
counts and artifact hashes are in `evidence/phase13/acceptance.json`.

[Hosted implementation regression 39947588324](https://github.com/Ledgercorp/BountyForge/actions/runs/39947588324)
confirmed the same 659 tests (650 passed, nine skipped), zero failures, and all
seven Node checks at `2b0272df2975994eddff59d788a93b32c7fbadbd`.
The original five MCP operations and five authorization refusals additionally
passed through a fresh real Codex client, including process termination and
reconnection; `legacy_mcp_compatibility.json` preserves that result. No original
evidence was overwritten.

Final review reproduced one durable-evidence defect in the initial queue:
completing a later proposal overwrote the previous receipt in its status row.
The public MCP transcript retained both, but local database history did not.
The corrected adapter appends complete results in a separate per-job receipt
history, with reservation ordinals and a hash chain, while retaining the latest
status view. Restarted status validates that history and exposes bounded receipt
summaries; corrupted entries fail closed. Existing pre-history records are
preserved as legacy records, without invented earlier history. The backing file
is bounded to 8 MB and remains private and gitignored.

A separate credential-free Docker acceptance replayed one deliberately wrong
proposal followed by the already-recorded Codex candidate. It passed all four
checks: failure remained failed, the recorded candidate required fresh passing
verification, both receipts survived restart, and corrupted history was refused.
`history_replay.json` contains the receipts. This generated no new repair and
starts no model calls. The final local suite executed **662 tests: 653 passed,
nine existing skips, zero failures**; Node checks remain 7/7. The increment from
659 includes a real-Qwen-artifact contract check and two history regressions.
