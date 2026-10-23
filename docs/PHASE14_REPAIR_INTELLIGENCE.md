# Phase14 — repair intelligence and owned maintenance capability

Checkpoint: `85729c3bcf4693627d50196ab81af1d783b8d88f`.
Branch: `engineering/revenue-linux-scout-20261021`. No production authorization.

## Implemented changes

The existing dual engines, MCP tools, owned queue and verifier remain the
architecture. The frozen validators and historical evaluation records are
unchanged. Six new hash-pinned maintenance cases exercise business logic,
decoded API response integration, helper dependencies, grouped data processing,
retry/error policy, event reduction and stock allocation. They are owned public
development material, with no stored reference patches. Only one function in one
approved source file is editable; helper functions remain read-only context.

Task preparation now reports bounded actual failing test identities/assertion
messages and AST helper dependencies. Traceback file paths and test source lines
are excluded. This is explicitly development feedback, not hidden evaluation
data. Both engines receive the same public problem/source and verification gates.

Qwen uses a new generation-only AST-bound grammar allowing up to three physical
lines per replacement, retaining assignment names, return prefixes and trusted
anchors. The original v2 adapter remains available; there is no provider or model
fallback. Every candidate still passes the unchanged syntax, binding, scope and
capability gates. Limits remain two attempts, three changes, 150 output tokens
per request, numerical loopback inference and the pinned runtime/model.

Retries distinguish rejected structure from actual regression failure. A retry
may retain prior model-generated sibling edits only after the entire previous
candidate passed source validation and then failed tests. A new edit at the same
anchor replaces its predecessor. The union must remain within three changes and
is fully revalidated from the original source; rejected source is never salvaged.
The raw model response, effective proposal, retained anchors, prompt hash and
actual failure feedback are recorded. No Codex patch enters Qwen generation.
Identical proposals/equivalent AST candidates still avoid repeated Docker work.

## Actual Codex development results

This active authenticated Codex session prepared tasks through the real native
MCP client, reasoned about the returned source and authored three new candidates:

| Task | Candidate attempts | Related edits | Targeted tests | Fresh replay tests |
| --- | ---: | ---: | ---: | ---: |
| invoice-summary | 1 | 2 | 8 | 8 |
| cursor-adapter | 1 | 2 | 7 | 7 |
| retry-policy | 1 | 1 | 7 | 7 |

All three passed and await owner review. No regressions or unauthorized file
changes were observed in those candidates. These are **3/3 developmental repairs**,
not independent generalization or commercial accuracy. The agent authored the
fixtures and could inspect their tests. The client starts no additional Codex
turn/API call; active-session tokens/model-call count are unavailable, not zero.
The bridge took 564.838 seconds including reasoning and tool intervals.

Trace: `evidence/phase14/codex_session.json`, SHA-256
`0ac58a876dd6d1eb7ab65633a1ec9c1f5f227a96638e7cba6aa41df2ed08fb96`.
The same trace includes two deliberately invalid security probes on a fourth
task: modifying a read-only helper and adding a filesystem callable. Both were
SOURCE_REJECTED before candidate execution; the probe exhausted its budget and
never became review-ready. Those QA inputs are excluded from repair accuracy.

All six defective baselines reproduced in admitted Docker (43 test methods,
six fresh twenty-control preflights). No reference fixes were used. The original
five MCP calls, five refusals and controlled kill/reconnection passed in a new
native client. Separate credential-free replay of the recorded candidates is
reported in `codex_independent_replay.json`, with no additional generation.

## Autonomous Qwen experiment

The opt-in standard public-Ubuntu workflow runs an actual owned QWEN_LOCAL queue
of invoice-summary, cursor-adapter and retry-policy. Qwen independently obtains
each prepared task, generates candidates, receives actual verification feedback,
retries or terminates, and commits bounded queue results. Maximum six local model
calls, one inference stream and one worker; no Codex session or provider key is
available in that workflow. Exact outcomes, usage and timings are published from
the completed run, not inferred from workflow success.

The harness checkpoints public owned evidence after preparation and each job.
Blocked admission/inference is classified separately from a failed repair.
All passing candidates require targeted tests plus a fresh Docker replay. Queue
history preserves attempts. No held-out or historical frozen inference is rerun.

## Evaluation and model feasibility

The public controller/agent exchange now freezes hash-bound task handoffs and
binds engine-specific submissions to source/task/verifier commitments. It rejects
answer/test fields, unbounded proposals, arbitrary paths and caller admission
flags. It neither executes supplied source nor grants independent-evaluation
status. The coding agent can access this checkout and write repository workflows;
withholding tests from MCP is not an enforceable unseen boundary. An independently
controlled verifier with tests inaccessible through the agent's filesystem,
tools and network remains unavailable. All Phase14 results remain developmental.

Official public metadata for larger Qwen Coder models was inspected at frozen
upstream revisions. The 3B Q4_K_M asset is 2,104,932,800 bytes; its Qwen Research
License is non-commercial only, so it is unsuitable as the default commercial
replacement without separate rights. The Apache-2.0 7B Q4_K_M asset is
4,683,073,536 bytes. Metadata, revisions and hashes are recorded in
`model_candidate_metadata.json`. Weights were not downloaded or executed, no
terms were accepted, and neither model replaced the pinned 1.5B runtime.
Resource estimates are not runtime/accuracy benchmarks. Replacement requires a
separately bounded measured CPU/memory/latency/quality experiment first.

## Admission and commercial status

Additional spending $0, revenue $0. No customer/private source, paid inference,
financial operations, production changes, recurring scheduling or delivery.
CODEX_AGENT intentionally requires the active session; no unattended Codex work
was pursued. QWEN_LOCAL remains the autonomous alternative. Private execution
is NOT_ADMITTED; unseen accuracy is unmeasured. Existing namespace/rootfs skips
remain separate from fresh owned Docker admission. Both PRs stay draft and main
remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`.

Next practical milestone: quantify the new autonomous queue's actual failure
categories, then benchmark a commercially usable larger model only under an
explicit resource envelope. Commercial readiness separately requires verified
quality, consent, payment/launch and owner-delivery gates; none follows from a
development score.

Local implementation checks: 673 Python tests executed, 664 passed, nine existing
skips, zero failures; Node 7/7; historical harness 10/10 (model-free). Frozen core
hashes and all prior fixture/evaluation files remain unchanged. The nine skips
remain eight unprovisioned namespace/rootfs tests plus one opt-in older catalog
replay; they are not counted as newly verified security checks.

## First hosted measurement and protocol correction

Commit `f6fdf1e1346f11f0a4f643ea6f6e6a61cbc9efe7` passed hosted regression
[39954099437](https://github.com/Ledgercorp/BountyForge/actions/runs/39954099437):
673 tests, 664 passed, nine skipped, zero failures; Node 7/7.

The real autonomous [Qwen run 39954093867](https://github.com/Ledgercorp/BountyForge/actions/runs/39954093867)
completed with **0/3 verified repairs**, six calls, 5,516 prompt tokens and
699 completion tokens. Experiment time was 97.931 seconds; generation calls
totaled 70.556 seconds. Four proposals were source-rejected and two source-valid
candidates failed targeted tests. No targeted suite passed. Cursor-adapter
introduced an UnboundLocalError by reading locals before assignment; it was
never marked verified. Raw evidence and receipt-bound scorecard preserve every
attempt, including retained sibling edits. These are developmental measurements.

Invoice proposals exceeded the schema's three-change limit. Retry proposals
were malformed or truncated. A new native llama.cpp schema transport is therefore
being tested; routing through the chat endpoint is not assumed to enforce the
schema. Two bounded diagnostic calls compare chat and native behavior using an
adversarial constant-valued schema. The native probe must pass before any of
the six repair calls are admitted. No provider/model fallback exists. This is a
new implementation experiment on the same exposed developmental material, not a
fresh independent evaluation.

Other corrections order authorized AST anchors by backward dependencies from
returned values, and reject newly introduced reads of locals before their first
existing binding. This additional static guard is conservative, not a general
control-flow proof. Original validators and all frozen artifacts stay intact.
The native transport uses the pinned server's own chat template, fixed loopback
paths, no proxies/redirects/credentials, bounded responses and the same 150-token
limit. Its real schema enforcement remains unverified until the hosted probe.

Local checks before this second experiment: 680 tests, 671 passed, nine skipped,
zero failures, plus a subsequent 16-test focused pass including non-object
transport rejection. Node 7/7. The subsequent extra regression scenario adds one
test to the next full count. No larger-model download or inference occurred.

## Native-schema measurement and raw-pattern defect

Commit `d9e6b088c8d8dbc7c007739f1f8d56a6cdae432b` passed hosted regression
[40000319972](https://github.com/Ledgercorp/BountyForge/actions/runs/40000319972):
681 tests, 672 passed, nine skips; Node 7/7.

[Qwen run 40000312299](https://github.com/Ledgercorp/BountyForge/actions/runs/40000312299)
completed: **0/3 verified repairs**, six repair calls plus two admission probes,
75.221 seconds experiment time. Both simple constant-schema probes passed.
Native repair responses still returned four changes on two first attempts.
Two retries were semantic no-ops; one source-valid cursor candidate failed
tests, and its equivalent retry was rejected without another Docker run.
No new test failure was observed compared with that task's defective baseline.
Switching transport did not improve measured repair success.

Investigation of pinned llama.cpp b11750's common/json-schema-to-grammar.cpp
found that pattern character classes are emitted over raw encoded text inside
quotation marks. Our negated-newline string pattern permits quotation marks
and JSON delimiters. An owned regression witness reproduces this mismatch:
`return value"},{"line":3,"new":"return value` matches the old string pattern.
The simple constant probe was insufficient to test the actual patch contract.
This is a generation-constraint defect; independent source validators caught
the invalid proposals and never admitted them as successful repairs.

The correction uses a small owned GBNF emitter with explicit JSON escaping,
fixed authorized numeric anchors, preserved assignment/return prefixes, at
most three edits and bounded continuation lines. The runtime's raw string
pattern conversion is not used for repairs. The v2/v3 interfaces and all
source validators remain intact. A full-contract adversarial grammar probe
now checks anchor and edit-count enforcement before any repair execution;
a deliberately invalid probe is tested to block queue creation. No test
solution is contained in the grammar or probe. A subsequent live run measures
this changed implementation only as development, with the same six-call
repair budget and two bounded admission calls.

## JSON-safe grammar measurement

Commit `b99c3f8a51c4c0737488d99457b615c2fef04992` passed hosted regression
[40001270229](https://github.com/Ledgercorp/BountyForge/actions/runs/40001270229):
685 tests, 676 passed, nine existing skips; Node 7/7. Local checks matched.

[Qwen run 40001263033](https://github.com/Ledgercorp/BountyForge/actions/runs/40001263033)
completed with **0/3 verified repairs**, six repair calls plus two admission
probes, 98.852 seconds experiment time. The actual full-contract grammar probe
passed. All six repair responses were parseable JSON within the three-change
bound, eliminating the prior structural violations in this small experiment.
Invoice still copied existing faulty statements; cursor retained incorrect
terminal-cursor logic; retry copied the faulty maximum clamp and altered
related assignments without solving the tests. All three second candidates
were rejected as repeated proposals/ASTs before repeated Docker tests. Two
source-valid first candidates failed targeted tests. No targeted suite passed;
no new test failure was observed relative to these defective baselines.
This improves measured contract adherence, **not repair success**. No more
inference tuning on these exposed cases is planned. The workflow returns to
manual-only operation; no schedule is active.

A separate one-call 7B CPU resource probe is prepared at the public official
Apache-2.0 asset/revision/hash recorded earlier. It uses the same verified
llama.cpp runtime, two CPU threads, 2,048 context tokens, a 10GiB process
address-space cap, bounded startup/request/CPU/log limits and a credential-free
child. Weights are disposable and not added to the persistent cache. The
probe generates only an explanation on an owned neutral question; it never
executes model output, changes the default, or measures repair accuracy.
