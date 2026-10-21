# Phase 5 engineering ledger

Objective: audit 24 old calls, improve measured repair performance without changing
the five historical cases, audit all 33 discoveries, preserve the $0 internal
execution boundary and existing operational pipeline. No production merge,
recurring repair schedule, upstream contact/submission or financial commitment.

## 2026-10-21: evidence recovery and implementation

Starting HEAD `773b2b0499117956b4c138696c78c1f5d6f834c7`; main remains
`22250921eb50b7a72e0f474b0f3ff329f81b55a8`. PR #1 remains draft.

Commit `81d231f` adds call-level historical audit, opt-in AST/contract context,
physical LF source addressing, fresh request metadata and Docker CPU/PID pressure
admission. Changed files are enumerated by `git show --stat 81d231f`; details in
PHASE5_REPAIR_ANALYSIS.md and PHASE5_SECURITY.md. Local checks at that milestone:
187 unittest cases, **180 passed, 7 skipped**; seven historical harness tests and
four Node dashboard tests passed. Later harness instrumentation adds an eighth
test; separate owned development admission adds nine unit tests.

Historical baseline: v3 and v4 each **0/5, 12 calls**. Recovered generation timing
24.826 s (four missing call latencies) and 72.212 s (two missing), respectively;
case wall time 49.15 s and 101.61 s. Raw historical responses are unavailable.
These are admitted model experiments, distinct from the earlier blocked namespace
run. No full upstream regression was performed.

Local managed cloud Docker pressure proof passed without changing limits:
64 tasks at PID denial, one denial event, CPU 3.035 s wall / 3.052 s use with
31 throttled periods. Four separate owned development baselines reproduced all
defects (12 tests: seven expected failures, five passes). No local model calls.

Hosted development comparison is pending. The existing curated workflow now
selects development or historical evaluation explicitly. Development runs legacy
then v5 sequentially, each at most eight calls; historical remains at most twelve.
Both use the original pinned Qwen/runtime and standard public ubuntu-24.04 runner.
The five historical source files, manifest and tests remain unchanged.

Deployment: no production or dashboard changes. Scheduling: no repair schedule.
Revenue $0; purchases/additional paid inference $0. No upstream external actions.
Seven legacy namespace/rootfs checks remain skipped; arbitrary repositories,
dependencies and full upstream execution remain unadmitted. Commercial audit and
independent historical evaluation remain in progress.

## Hosted development and qualification (before historical freeze)

Commit `c0af34d51df814c08a89a50515e467eb290e1be0` passed hosted regression
[39599150161](https://github.com/Ledgercorp/BountyForge/actions/runs/39599150161):
196 unittest cases (**189 passed, 7 skipped**), eight harness and four Node tests;
read-only synthetic discovery and evidence validation passed. Hosted development
[39599142565](https://github.com/Ledgercorp/BountyForge/actions/runs/39599142565)
passed on the original pinned Qwen and standard public Ubuntu runner:

| Owned development protocol | Verified repairs | Calls | Inference seconds |
| --- | --- | --- | --- |
| legacy | 3/4 | 5 | 26.614 |
| ast_contract_v5 | 4/4 | 4 | 20.990 |

Legacy ran first on the same server; timing may benefit from warm caches on v5.
This is one comparison of the complete protocol, not an isolated causal study or
a commercial-success prediction. All four v5 tasks passed on their first calls.
Raw artifact digest is `1ec7b3bd0fd5885935e654226cd7fe964e01312d1a017084edee22110f98ad33`;
unmodified reports are retained under `evidence/phase5/hosted-*`.
Hosted pressure admission passed: 64 tasks at denial, one denial event, CPU
3.061 s wall / 3.066 s use / 31 throttled periods, plus all earlier controls.

The 33-record current commercial audit is complete: 31 open / 2 closed,
0 commercial verified / 21 rejected / 12 unknown. All 33 fail the current Python
profile; no owner-review candidate or execution authorization. Seven dimensions
and bounded primary-source snapshots per record are documented in
PHASE5_COMMERCIAL_AUDIT.md. Inaccessible funding pages and eligibility/policy
uncertainties remain unknown. Neither dashboard v11 nor durable state changed.

Independent review found and corrected loss of active-call evidence on interruption,
Unicode physical-line diff formatting, and mislabeling sandbox unavailability as
a model test failure. Ten harness tests now cover those paths. The separate
historical verifier reconstructs only recorded validated model proposals, matches
their exact patches and reruns successful cases in freshly admitted Docker, with
zero new inference. Protocol assets are frozen in `evidence/phase5/protocol-freeze.json`
before independent historical evaluation. No historical result has yet changed.
