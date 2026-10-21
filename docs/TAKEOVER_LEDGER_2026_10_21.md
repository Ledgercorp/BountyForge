# BountyForge takeover ledger — 2026-10-21 UTC

## Recovery

Recovered engineering HEAD `97d04a20e31d8f618e07b5698d39482dbd71f3a6`.
Main remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`. Both historical
commits specified by the owner are ancestors. PR #1 remains draft; repo public.
Cloud checkout only; no Mac or unrelated projects accessed.

Executed baseline: 147 unittest cases, 7 skips (140 executed passes), and
5/5 historical harness tests. Earlier reports saying “147 passed, 7 skipped”
used unittest's total count, which includes skips.

Run 39536935263 failed before inference with
`unshare: write failed /proc/self/uid_map: Operation not permitted`.
This establishes denial of UID mapping, not the exact kernel/LSM rule responsible;
the original run did not collect sysctl/AppArmor audit data. No model attempts.
Later runs 39537540798 and 39537920526 used the pinned Docker image, reproduced
all five baselines and measured 0/5 repairs with ten calls each. Latest run's
logs and downloaded artifact were inspected during recovery. Failures included
nonmatching snippets, truncated JSON, invalid syntax and incorrect patches.

## Curated boundary and shared line protocol

Files: `bountyforge/curated_docker.py`, `bountyforge/curated_tasks.py`,
`benchmarks/phase4/benchmark_runner.py`, its harness tests,
`tests/test_curated_docker.py`, `tests/test_curated_tasks.py`, and curated workflow.

Three negative regression tests first reproduced forged-marker acceptance of
arbitrary source, changed acceptance tests and Python startup files. Fixed by
binding admission to exact curated files/tests and replaying changed source
through existing `stage_lines`, with unchanged declaration protection.
Task symbols select AST statement starts and referenced global data definitions;
no issue-specific solution text or model-selected paths/commands are introduced.
Two rounds maximum per case; 454 has two symbols, giving at most 12 calls total.
The prior snippet staging API remains only for its existing validation tests.
Removed namespace/host execution fallback entirely.

Executed on Codex Cloud Linux Docker: non-root, no capabilities, no_new_privs,
seccomp active; network and model loopback unreachable; root/source writes denied;
Docker socket and credential variables absent; 256 MiB memory kill, no swap,
1 CPU quota, 64 PID limit read back, 64 MiB noexec tmpfs, wall timeout and cleanup,
and output cap verified. PID and CPU quota values were read back; exhaustive
kernel escape testing is not claimed. Trusted inline probes run before excerpts.
A Docker --rm/removal race was observed and fixed with bounded absence checking.
No certification for arbitrary hostile repositories is claimed.

After changes: 155 unittest cases, 7 skipped (148 executed passes); 6/6 historical
harness tests passed. Live original-baseline reproduction and hosted model run
are recorded in later entries after execution. All original fixtures and tests
remain unchanged. No full upstream Boltons suite has been run.

Deployment: feature branch only; no production deployment or schedule enabled.
Infrastructure: existing public standard-runner Actions and Codex Cloud Linux.
Additional resources purchased $0; paid model APIs 0; confirmed revenue $0.
External submissions/claims/messages 0. No larger runners or new cloud services.
Remaining: hosted new benchmark, durable state, operational negative scenarios,
commercial verification and safe scheduling gates.

## Hosted shared-line measurement

Implementation commit: `026e85d766ac9b9e732ae9c1b739e4bd1effbe0e`.
[Historical run 39590337663](https://github.com/Ledgercorp/BountyForge/actions/runs/39590337663)
passed all live admission controls and reproduced 5/5 baselines. **0/5 repairs,
12 actual Qwen calls, zero blocked cases**. Four calls were for the two-symbol
454 case; other cases used two. Its artifact was downloaded and inspected.
[Regression 39590343470](https://github.com/Ledgercorp/BountyForge/actions/runs/39590343470)
succeeded. No claim of full upstream regression or commercial readiness.
Local Docker baseline checks initially encountered unreadable task directories
from the cloud checkout's restrictive umask; public fixture read permissions were
normalized locally, then all five baseline assertion failures reproduced.

## Durable operational acceptance implementation

Files added: `bountyforge/durable.py`, `scripts/coordinate.py`,
`scripts/security_acceptance.py`, operational workflow, durable/control tests,
and `docs/BOUNDED_OPERATIONS.md`. Existing Queue, operator, worker, scope gate,
qualification, opportunities and synthetic CLI were extended, not replaced.
All model workflows share one repair concurrency group. Manual discovery removes
checkout credentials. No active cron was added.

New negative tests first reproduced concurrent SQLite claims, duplicate source
functions, unnecessary inference retry and inference on a baseline import error.
Fixes: one active claim, fenced completion, declaration ambiguity rejection,
assertion-only baseline, stop on endpoint timeout, offline Docker for the new
internal operational worker. Commercial grading no longer makes an unfunded
advertisement actionable. No current adapter independently establishes funding.

Executed locally: **170 unittest cases, 7 skips (163 executed passes)**;
**6/6 benchmark harness tests**; **16/16 scripted operational scenarios**.
Scripted/injected tests are labeled and do not claim real-Qwen failure injection.
The synthetic Docker boundary also passed live controls and reproduced addition.
GitHub reports one 1,091,948,032-byte cache and 26,103 bytes in 17 artifacts before
this operational experiment. No paid resources or APIs were created. Billing
invoices are not available here; no new chargeable service was requested.

Deployment: feature branch only. Scheduling inactive. External submissions 0;
confirmed revenue $0. Hosted durable-cycle evidence is pending the tagged run.

## First hosted durable cycle

Implementation commit: `28ec65d017d3e755a86652e1d8d6fcd92e08ea9c`.
[Operational run 39591802636](https://github.com/Ledgercorp/BountyForge/actions/runs/39591802636)
completed **discovery, coordinate, repair and record jobs successfully**. This is
an internal synthetic cycle, not a paid bounty. Its exact ledger/evidence and
subsequent duplicate/recovery tests are inspected in later entries.
Hosted regression run 39591809618 also succeeded. No schedule activated, no main
merge, no upstream submission, no revenue. Same standard public Ubuntu runners.

Next measured experiment changes only generic prompting: concise instructions,
explicit target symbol and a JSON schema enumerating caller-approved line
numbers. The existing staging validator is unchanged. Qwen and runtime stay
pinned. Same original five cases, at most twelve calls; results pending execution.
