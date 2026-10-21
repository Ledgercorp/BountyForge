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
