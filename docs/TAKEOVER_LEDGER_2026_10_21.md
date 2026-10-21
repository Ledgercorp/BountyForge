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

## Repeated hosted operation and final historical experiment

Commit `4eff34d8e09be4687fac4322d294f8128e575dd0`:
[second complete cycle 39592153607](https://github.com/Ledgercorp/BountyForge/actions/runs/39592153607)
passed all four jobs with real local Qwen and durable evidence.
[duplicate cycle 39592910695](https://github.com/Ledgercorp/BountyForge/actions/runs/39592910695)
passed discovery and coordination, correctly skipping repair and publication;
no duplicate inference. The remote ledger was independently read: two completed
synthetic jobs at exact source revisions, 21 unverified discoveries, no real
commercial review-ready result.

[Historical run 39592095298](https://github.com/Ledgercorp/BountyForge/actions/runs/39592095298)
measured **0/5, 12 calls, 5/5 reproduced baselines, zero blocked cases**. Model
responses ended normally; the concise symbol/line-enum experiment did not solve
the defects. Persisted its complete bounded receipt in
`evidence/hosted-boltons-2026-10-21.json` so results outlive artifact expiry.
The two new historical experiments together used 24 actual model calls. Earlier
115/240-token historical trials remain separate. No manual solution counted.

## Security and owner dashboard follow-up

Six new payload subtests reproduced that syntax-valid edits could add process,
file, dynamic execution or object-introspection capabilities. The line validator
now blocks these capabilities, preserving all declaration checks. A separate
negative test reproduced treating Docker daemon failure as successful cleanup;
cleanup now requires an explicit container-not-found response.

Real local HTTP tests verify connection refusal, bounded timeout and redirect
rejection. A first test run hit TCP TIME_WAIT (`Address already in use`), causing
one error in 178 cases and 15/16 scenario acceptance; the fixture now uses socket
reuse, and subsequent full runs passed. No hidden failure was relabeled success.
Independent publication now binds the fixture fingerprint, patch fingerprint,
exact revision, execution timestamp and active lease; a forged-source test
first reproduced the missing check. SHA digests detect changed content; trusted
same-repository workflow provenance supplies authority, not the digest alone.

Final local worktree verification before this follow-up commit: **179 unittest
cases, 7 skipped (172 executed passes)**; **6/6 historical harness tests**;
**4/4 Node dashboard projection tests**; **16/16 failure scenarios**. Actual
loopback timeout/refusal and separate injected worker retry faults are labeled.
Live Docker controls passed again after cleanup hardening.

The existing BountyForge Hatchable project alone was inspected. Personal/private
visibility remains; daily read-only discovery cron is active with two successful
recorded fires and zero recorded errors. No repair schedule is active. Its old
operator status incorrectly said hosted work was absent. Prepared an admin-only,
read-only GitHub-ledger adapter and a status panel, tested via authenticated
platform execution: admin 200, public 401, ordinary member 403; deployment dry
run has no errors/warnings. No new keys, paid services or write tokens on the
site. Private dashboard source was not copied into the public repository; only
newly authored adapter, projection and panel files are tracked. Deployment
version/result is recorded after execution.

Read-only sampling of primary discovery records found false positives:
Naris404/clash_royale_rl_agent #41 describes RL reward shaping, not monetary
payment; kwilson21/tally #738 describes paid-invoice matching, not an offered
bounty. Both remain unverified/non-executable. This is not an exhaustive market
audit and establishes no payable opportunity.

Readiness: DRY_RUN_READY for bounded owned-fixture cycles; NOT_READY for real
paid bounty repairs. Main unchanged; draft PR preserved. No recurring Actions
repair schedule, automatic upstream steps, new spending commitments, paid model
APIs, confirmed bounty revenue, Mac access or external submissions.

## Latest security acceptance and deployed owner status

Implementation commit `e3161fff96a8cb45af45c73e7f7e0c191893a8e1` passed
[full operational run 39593624581](https://github.com/Ledgercorp/BountyForge/actions/runs/39593624581):
179 unittest cases (7 skips, 172 executed passes), 6 harness tests, 4 dashboard
projection tests, 16 operational scenarios, pinned-model verification, isolated
real-Qwen synthetic repair, independent publication and durable completion.
This is the third successful complete internal hosted cycle. Regression run
39593631825 also succeeded. A simultaneously triggered CPU acceptance workflow
was cancelled without inference, and the unrequested historical workflow skipped;
these are not failed model attempts.

Dashboard v9 deployed successfully to the existing **personal/private** project;
admin status execution returns 200 and its projection reads the durable ledger.
The public/member restrictions remain 401/403. Its fixed raw-GitHub URL was then
observed returning an earlier cached state after completed publication. Follow-up
adds a 30-second cache-busting key and retains the explicit distinction between
coordination leases and model health. Status with no completed cycles no longer
labels a worker as verified. Final deployment and original three-case compatibility
run are recorded after execution. No paid services, external submissions or
repair cron were enabled.

## Final compatibility and dashboard verification

Commit `abef9009878b1b83b88c392526ee45148e453a44` passed
[original CPU acceptance 39594116526](https://github.com/Ledgercorp/BountyForge/actions/runs/39594116526)
with the new validator and generation constraints. This preserves the previously
proven synthetic path; the exact three-case receipt is checked in the final
summary. Regression run 39594123115 also succeeded.

The raw GitHub branch URL remained stale even with the query key, so that first
cache mitigation was not sufficient. The fixed read-only GitHub Contents API
route was tested next and returned the actual current blob
`2b01078f2700f43e43812811bd2c9f9f52616b88`: **three completed synthetic cycles,
zero active/expired leases, 25 unverified discoveries**. The adapter exposes the
blob SHA and observation time, fails to unknown on read errors/rate limits, and
uses no authentication credential. No claim of constant model availability.
Dashboard regression path coverage now includes `dashboard/**`.

Final security checks not performed/claimed: arbitrary hostile-repository
certification, full upstream Boltons suites, comprehensive kernel-escape review,
CPU/PID pressure stress tests beyond live cgroup limit readback, and full browser
rendering of the private dashboard. Namespace rootfs tests remain seven explicit
skips. Actual live negative Docker, HTTP and validator tests are documented above.
All original historical task sources, manifest and acceptance tests are unchanged
from recovered HEAD. Both required historical commits remain ancestors. Main
stays the production baseline; PR #1 remains draft.

Owner-facing status deployment: v9 then v10 were live/private; final Contents API
adapter is verified in draft execution and committed before final deployment.
The final version and PR/regression links are listed in the final acceptance
summary. No external bounty claim, outside PR, email, message, contract, account
registration or financial commitment occurred. No paid inference, larger runner,
Oracle VM, new paid infrastructure or Mac access. Additional authorized purchases
$0, confirmed revenue $0; account invoices were not independently audited.

**DRY_RUN_READY** for complete bounded internal cycles. **NOT_READY** for real
paid bounty operation. Recurring repair scheduling remains inactive: default
branch activation would advance beyond the preserved production baseline while
real-code safety, funding and repair-reliability gates remain unsatisfied.

## Hosted interruption and conditional-write probe

Commit `89f5e8738e68265b1c08d3fcda6279226509ba81` adds an explicit manual-only
recovery-probe input; normal leases remain 900 seconds. Probe leases are ten
seconds, validated by the same Queue bounds. Local regression: 180 cases,
7 skips (173 executed passes), 6 harness tests and 4 dashboard tests.

[Probe run 39594818372](https://github.com/Ledgercorp/BountyForge/actions/runs/39594818372)
**failed intentionally with exit 75** after persisting a claim and proving the
live GitHub Contents API rejected an update with a stale SHA. Its discovery
passed, repair/publication skipped and model calls were zero. This is an expected
fault-injection failure, not a repair failure or a falsely successful workflow.
The remote ledger was independently read after termination: running, attempts 1,
expired lease, no result. A second workflow instance at exactly the same revision
([recovery 39595024636](https://github.com/Ledgercorp/BountyForge/actions/runs/39595024636))
was dispatched normally; its result is recorded in the final acceptance summary.

Original synthetic compatibility is confirmed from logs: run 39594116526
verified pinned model/runtime hashes, addition canary, and **3/3 original owned
synthetic repairs** after capability hardening. Latest dashboard v11 is live and
private (deployed 2026-10-21T11:48:31 UTC). Current Contents-based status exposed
three completed cycles, no active/expired leases and the exact ledger blob SHA.

A final read-only runner-policy snapshot was added to regression artifacts to
inspect current AppArmor/user-namespace sysctls, process capabilities and seccomp.
It does not modify policy or retry the rejected unshare mechanism. A current
snapshot cannot prove the exact historical kernel/LSM audit rule from the original
run; that attribution remains explicitly limited to the observed UID-map EPERM.

## Completed recovery and final reporting safeguards

Recovery 39595024636 passed all four jobs at the exact interrupted source
`89f5e8738e68265b1c08d3fcda6279226509ba81`. The authoritative ledger confirms
claim attempts 2, `synthetic_review_ready`, evidence digest
`7e014b9673334901bed3fb5c7e393f427502e827291fe582b82d2cf914420d6e`, no active
lease and no commercial approval. Four complete cycles and 33 unverified
opportunities are captured in `evidence/hosted-durability-2026-10-21.json`.
Recovered envelope and 16/16 scenario receipts were independently read and saved.

Regression 39595287888 passed against source `dc3b6f329ee003c3b0fe95265bdda4ca95b56a74`
(PR test-merge SHA `daffadd176699792c6ed8169918b7692c68368d2`). Current namespace
policy snapshot shows AppArmor restriction enabled, userns clone enabled, max
58121 namespaces, no effective capabilities, host seccomp 0 and AppArmor among
active LSMs. Different runner image from the original failure; no historical
audit-rule attribution or policy bypass is claimed.

A final reporting audit found that the historical workflow's always-upload paths
could include an old tracked score if admission failed. Artifacts now come only
from a fresh run directory. Calls are counted at actual client invocation, and
blocked cycles explicitly say `no_inference`. A new harness test first reproduced
the incorrect inference label, then verified 5 blocked cases, 0 calls and 0
attempted repairs. This adds no new Qwen score. Final local regression: 180 cases,
7 skips (173 executed passes), 7/7 harness tests and 4/4 dashboard tests.

`docs/FINAL_ACCEPTANCE_2026_10_21.md` consolidates exact commits, executed runs,
files/components changed, deployed v11, inactive repair scheduling, spending,
external actions, skipped checks and remaining blockers. No external submissions
or received revenue. PR #1 remains draft; main and repository visibility unchanged.
