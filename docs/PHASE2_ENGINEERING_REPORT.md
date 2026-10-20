# LEFTSOCK LABS | BOUNTYFORGE
## Phase 2 engineering acceptance report
**Evidence cutoff:** October 20, 2026, 12:13 UTC  
**Repository:** https://github.com/Ledgercorp/BountyForge  
**Integrated-code commit:** `9a4f6a3f80bf75696e538f6e3ffcbbed5b5d69ad` (before addition of this report)  
**Private dashboard:** https://leftsock-bountyforge.hatchable.site (v6)  
**Status:** Synthetic autonomous repair **proven**; unrestricted production bounty execution **not admitted**.

### 1. Baseline and architecture
Preserved the previously verified Qwen2.5-Coder-1.5B-Instruct Q4_K_M model (1,117,320,768 bytes; SHA-256 `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`), official llama.cpp b11750 CPU runtime, prior model and prompt receipts, scanner, historical commits and owner-private Hatchable dashboard. No existing project was rebuilt.

### 2. Implementation changes
- `bountyforge/worker.py`: fixed-command Python unittest runner, controlled synthetic fixtures, bounded per-attempt file and subprocess access, env stripping, time and CPU limits, subprocess-group kill on timeout, deterministic source fingerprint, strict patch validation, original baseline failure requirement, maximum two model attempts, pass/fail evidence and review-only diffs.
- `bountyforge/queue.py`: SQLite WAL idempotent enqueue, transactional claims, 900-second maximum lease, two-claim exhaustion and durable terminal results.
- `bountyforge/operator.py`: claims at most one task, resolves only a trusted fixture catalog, records explicit success/failure. Unrecognized tasks fail closed.
- `bountyforge/evaluation.py`: explicit screening for verified issue URL, original provider status, issue state, numeric reward, supported language, AI permission, US eligibility, no paid prerequisites and acceptance conditions. Never treats a platform advertisement as escrow or verified income.
- New tests and `fixtures/controlled/addition/` plus `scripts/phase2_demo.py` for opt-in reproducibility.
- Hosted `/api/operator-status` and dashboard v6: owner-authenticated actual scan ledger, explicit hosted-model-unavailable state, no invented submissions or earnings.

**Execution scope:** Only checked, deliberately broken local synthetic fixtures may execute tests. This is **not** a security boundary adequate to run arbitrary third-party repos. `subprocess` limits and temporary directories do not provide independent network, kernel or filesystem isolation. No third-party test suite was executed.

### 3. Complete test results
- Expanded Linux suite: **42/42 passed** in **73.358 seconds** after correcting an intermittent timeout allowance. Exact log retained at `/mnt/data/bountyforge_build/phase2-final-retest.log` in the temporary execution environment.
- One earlier full-suite run: **40/41 tests passed**, with an intermittent queue-to-worker integration failure due to test-runner timing in the shared CPU environment. The fix preserved bounded execution and added a specific timeout-kill regression. Subsequent 42-test full rerun passed.
- Suite covers: schema and safe paths, symlinks, malformed JSON, forbidden files, fake-model failure and success, correction attempts, baseline non-failure, no paid API fallback, token budget, queue idempotency, crashed lease recovery, exhausted leases, safe evaluation, operator one-job behavior and subprocess timeouts.

### 4. Independently verified real inference
On a temporary Linux CPU environment using the actual Qwen GGUF and locally bound llama.cpp endpoint, `repair_fixture` received a structured issue, inspected an allowlisted `calc.py`, required the original tests to fail, called Qwen once, parsed its constrained structured response, generated a diff, wrote the proposal only to a disposable copy, reran tests and returned `review_ready`.

**Observed receipt:** `evidence/phase2_real_cpu_repair.json` in the repository, backed by the full temporary local receipt `real_model_dryrun.json`.
- Baseline: 2 failing unittest cases; subprocess exit 1, 2.505 seconds.
- One genuine local-model inference request; no paid API.
- Patch: `return a - b` changed to `return a + b`.
- Verification: 2 test cases passed; process exit 0; 2.628 seconds.
- Whole cycle: **18.888 seconds**.
- No changes to original fixture or external repo. No PR, bounty claim or payment initiated.

This proves one small synthetic software repair. It does **not** prove reliable complex issue solving, sandbox escape resistance or commercial fitness.

### 5. Failure and recovery
Controlled negative scenarios passed: malformed model JSON, incorrect patch producing failing tests, model unavailability, attempted forbidden test-file change, invalid allowlist, baseline unexpectedly passing, prohibited symlink/file paths, duplicate queue entries, expired leases and a killed timed-out child. Only a test-passing reviewable patch can have the `review_ready` status; submitted/paid state is never set by this pipeline. Queue lease exhaustion becomes a recorded `failed` terminal state.

### 6. Hosting and operating model
- Hatchable personal/free project v6: private UI, owner-gated HTTP endpoints, Postgres scan persistence and a working daily **12:00 UTC** discovery cron. The scheduled scan first fired on October 20, 2026; at verification 4 saved scans and 25 unverified candidates existed.
- Qwen inference: actual CPU execution proven in this temporary Linux workspace, **not** deployed for unattended inference. Hatchable function runtime cannot spawn/run a persistent llama.cpp process.
- Hugging Face free CPU Basic hardware exists, but Hugging Face now says creating new compute-backed Spaces requires a paid plan. The linked HF account was non-Pro. This route was not used.
- Google Colab is neither a reliable permanently available inference server nor a suitable unattended production runner.
- Private GitHub Actions can charge after an included monthly allocation. No automated Actions inference schedule was enabled without verifying available quota/billing restrictions.
- Strongest admitted setup today: **durable scheduled discovery + on-demand temporary Linux CPU repair**. Continuous autonomous paid-bounty repair remains blocked.

### 7. Bounty market audit
Original platform pages were cross-checked against linked GitHub issues. The primary-source comparisons are recorded in `evidence/phase2_bounty_evaluation.json`.

| Candidate | Advertised reward | Original evidence | Decision |
|---|---:|---|---|
| PHPUnit empty coverage file warning #4440 | Opire $50 available | https://app.opire.dev/issues/01HWX4P9F1935V3ZXN4TY7VDEQ ; https://github.com/sebastianbergmann/phpunit/issues/4440 | Rejected: GitHub issue closed March 31, 2026; PHP unsupported by Phase 2 worker |
| GritQL hanging comma #416 | Algora $50 historical | https://algora.io/grit/bounties ; https://github.com/biomejs/gritql/issues/416 | Rejected: closed/rewarded October 2024; current Algora page shows zero open bounties |
| Zod inference #2654 | Algora $25 listing | https://algora.io/triggerdotdev/bounties ; https://github.com/colinhacks/zod/issues/2654 | Rejected: GitHub closed Aug 13, 2026; TypeScript not admitted in synthetic executor |
| UdioWrapper #7 | Opire $120 available (6 reported rewards) | https://app.opire.dev/issues/01HW8CK374Y67WDDZG22BYVZQ4 ; https://github.com/flowese/UdioWrapper/issues/7 | Rejected: captcha bypass and reverse-engineered third-party API; unverified AI/US/payment eligibility; many competing attempts |
| Claude changelog skill #1 | GitHub advertises $50 | https://github.com/claude-builders-bounty/claude-builders-bounty/issues/1 | Rejected: platform funding record not independently verified; no confirmed unclaimed work and severe contributor competition |

**Funded-and-eligible bounty count: 0.** An apparent dollar figure and a platform `Available` label do not by themselves prove held funds, noncompetition, rules, AI permission, jurisdictional eligibility or eventual payment. Therefore there is **no approved real bounty patch or submission packet**.

### 8. Autonomous evaluation
Deterministic `evaluate()` tracks precise rejection reasons. Even an otherwise reviewable opportunity is **not** marked `funding_verified` or `eligible_for_execution` by a keyword match or platform advertisement. This prevents the research stage from upgrading an ambiguous lead into a paid job without separate evidence.

### 9. Dashboard acceptance
Hatchable project ID `proj_IXx0xMsdZDSg`, v6, owner-private URL `https://leftsock-bountyforge.hatchable.site`.
- `/api/operator-status` HTTP **200** for authorized owner, **401** for anonymous user.
- Real Postgres returns **4** saved discovery scans and **25** latest candidates; next scheduled run October 21 at 12:00 UTC.
- Hosted AI and active hosted jobs display **not deployed/0**. Verified payments, pending public submissions and external attempts all display **0**. Platform account billing was **not independently retrieved**; not falsely displayed as a confirmed $0 bill.

### 10. Spending and revenue
- **Paid model API calls:** 0.
- **New paid compute or infrastructure provisioned:** 0.
- **New billable GitHub Actions runs initiated for this phase:** 0.
- **New spending authorized:** $0.
- **Provider invoice audit:** Not available; total platform charges not independently confirmed.
- **Confirmed received bounty revenue:** **$0**.

### 11. What remains before real autonomous earning
1. Establish independently enforced host isolation for untrusted third-party tests: network namespace restrictions, mount isolation, read-only base, identity isolation, strict CPU/memory/disk/time and credentials exclusion. Current worker is **synthetic-fixture only**.
2. Admit free scheduled or on-demand CPU service with verified no-overage billing and persistent model/queue recovery. No unproven always-on hosting claims.
3. Improve provider-specific opportunity verification with actual funding/payout status, U.S. eligibility, AI policy and current GitHub status and PR competition.
4. Find one live, explicitly eligible, low-complexity bounty with verifiable payment terms; reproduce and validate its solution locally.
5. Obtain owner approval before any external bounty claim, issue comment, public PR, financial action or third-party repository write.

### 12. Completion assessment
**Engineering milestone achieved:** a bounded Qwen-driven end-to-end synthetic repair, tests and queue/recovery infrastructure with reproducible evidence, a privately deployed live operations dashboard, and evidence-based real-bounty rejection screening.

**Commercial milestone not achieved:** no demonstrated production-grade arbitrary-repository isolation, no continuous unattended inference and **no first real funded submission or earned dollar**. The Phase 2 target is therefore **partially complete** rather than production-ready.