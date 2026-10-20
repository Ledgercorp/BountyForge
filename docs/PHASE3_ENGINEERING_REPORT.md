# LeftSock Labs | BountyForge Phase 3

## Evidence-based engineering report | October 20, 2026

**Status:** Phase 3 partially completed. No third-party repository was modified. No bounty claim was filed and no revenue was received. The unattended model worker is not deployed. Extra infrastructure spending was not authorized or incurred in the engineering steps; independent provider billing totals were not retrieved.

### 1. Source and custody

- Continued from the established private GitHub repository `Ledgercorp/BountyForge`, starting from the previously confirmed Phase 2 commit `a11ec40108bafb508bf55da16fb0e4166c9d3e4d`.
- Original verified Qwen2.5-Coder-1.5B Q4_K_M GGUF and llama.cpp CPU runtime were reused. The previous synthetic-model repair receipt was preserved, not regenerated.
- New Phase 3 source files: `bountyforge/isolation.py`, `isolation/capdrop.c`, `isolation/launcher.sh`, `isolation/build_rootfs.sh`, `tests/test_isolation.py`, `bountyforge/opportunities.py`, `tests/test_opportunities.py` plus evidence and an upstream-derived issue reproduction.
- Dashboard v7 deployed in the existing owner-private Hatchable project at https://leftsock-bountyforge.hatchable.site . Existing read-only daily discovery and database-backed metrics were preserved.

### 2. Isolated Linux test runner

The executable prototype was tested using unprivileged user, PID, network and mount namespaces (`unshare -Urnmpf`), a small chroot filesystem containing offline Python 3.13, a 32-MiB tmpfs for test files, dropped Linux capabilities, `no_new_privs` and seccomp-denied process cloning, network sockets, mounts and related privileged system calls. The parent enforces a 2–30-second wall-time bound with process-group kill. Guest RLIMITs additionally cap CPU time, virtual address space, per-file writes, open files and core dumps. No internet access, package installation or arbitrary shell command is available inside the test runner.

**Acceptance: 7/7 boundary tests passed.** They covered denied outbound socket creation, denied process fork, hidden host filesystem and `/proc` data, failed-test propagation, timeout termination, symlink refusal and malformed/missing runner configuration. The host has a **read-only cgroup filesystem**, so stronger memory/IO/pids cgroup enforcement is unavailable. The syscall filter is a denylist, not a complete allowlist. A rootless namespace/chroot alone is not a certified hostile-code security boundary. Accordingly the normal BountyForge worker remains restricted to controlled synthetic fixtures, and third-party automation remains **disarmed**.

### 3. Real open-source issue engineering

- Original open issue: https://github.com/mahmoud/boltons/issues/524
- Original source: https://github.com/mahmoud/boltons/blob/master/boltons/strutils.py
- Source GitHub blob SHA: `74441c7e39dc5a666d76ca559f2ea6b80b3372c6`.
- Scope: a **faithful excerpt of the upstream `bytes2human()` implementation and its unit constants**, NOT a complete clone or checkout of the Boltons repository. No third-party dependency installation.
- Reproduction: `bytes2human(1048575)` produced `1024K` instead of `1M`; `bytes2human(1023.5)` produced `1024B` instead of `1K`; `bytes2human(1023.99,1)` produced `1024.0B` instead of `1.0K`. Baseline tests **3 failed / 2 passed**.
- **Real Qwen attempt 1:** rejected by allowlist/path validation. **Real Qwen attempt 2:** rejected because proposed output was not syntactically valid Python (it used a placeholder string). No code was applied from either model attempt. The bounded real-issue AI success rate was **0/2**.
- A **separate assistant-authored corrective diff**, clearly not attributed to Qwen, promoted units when rounding would display 1024 of the smaller unit. The isolated excerpt test suite then passed **5/5**, with a zero exit code. Patch: `evidence/issue524_assistant_draft.diff`.
- Limits: passing five excerpt-focused tests does **not** establish correct behavior across the whole module, full upstream test suite, supported interpreter versions or all rounding edge cases. No upstream CI run or PR submitted. The issue is **unfunded in the verified evidence** and is an engineering case study, not a revenue candidate.

### 4. Tests and negative scenarios

Full locally available BountyForge regression suite: **61 tests passed, 0 failed** using `/usr/bin/python3.13`; elapsed **11.092 seconds**. Log: `evidence/phase3_regression_61_tests.log`. The 61 comprise the previous synthetic-stage unit tests plus 7 isolation tests and 12 opportunity-gating tests. Initial runs using a Python virtual environment exceeded the execution allowance. Re-running under the system interpreter completed successfully; earlier timeouts are not counted as passes.

Existing Phase 2 real Qwen synthetic fixture acceptance remains proven. The new source-excerpt task did **not** pass via the autonomous model. Two rejected attempts were captured. The real-source assistant correction passed tests but is not approval-ready for full-repository submission.

### 5. Funded opportunity audit

Independent source reconciliation identified **six records** across GitHub, Algora and Opire. None was fully eligible for unattended BountyForge execution; no independently confirmed escrow was found.

| Source and original issue | Observed reward | Classification | Disposition |
|---|---:|---|---|
| Algora / [nuclei #6674](https://github.com/projectdiscovery/nuclei/issues/6674) | $100 advertised | Tier C | GitHub closed; Go, already completed |
| Algora / [nuclei #6532](https://github.com/projectdiscovery/nuclei/issues/6532) | $100 advertised | Tier C | GitHub closed; prior implementation |
| Algora / [sxt-proof-of-sql #560](https://github.com/spaceandtimefdn/sxt-proof-of-sql/issues/560) | $200 advertised | Tier C | GitHub closed; large Rust task |
| Algora / [highlight #8032](https://github.com/highlight/highlight/issues/8032) | $20 advertised | Tier B, **ineligible** | Issue open, but old unresolved scope, competing PRs, JavaScript/TypeScript, payer/AI/US conditions need confirmation |
| GitHub / [boltons #524](https://github.com/mahmoud/boltons/issues/524) | None verified | Tier C | Open Python issue useful for engineering, no rewarded offer identified |
| Opire / [zeroeye listing](https://app.opire.dev/issues/01KWQ0VT1N2TKGCY1CK9T61C1Z) | Unverified unusual amounts | Tier C | Payment funding/issuer and linked GitHub issue not independently verified |

Supporting original marketplace listings: [Algora ProjectDiscovery](https://algora.io/projectdiscovery/bounties?status=open), [Algora Highlight](https://algora.io/highlight/bounties?status=open), [Algora Space and Time](https://algora.io/spaceandtimelabs/bounties?status=open).

**Tier A: 0, Tier B: 1, Tier C: 5, actionable: 0.** Tier B means an identifiable public reward offer while conditions remain unverified, **not** funded escrow or a promised payout. Opire explicitly documents that payment is arranged by the individual creator after review: https://docs.opire.dev/rewards/pricing . BountyForge now rejects user-supplied escrow claims from being promoted to Tier A. No source adapter has yet demonstrated independent escrow verification.

### 6. Operating and hosting feasibility

- Qwen inference: independently verified on a temporary Linux CPU host in Phase 2. It is **not** continuously running as a commercial service.
- Hatchable: private v7 UI, persisted scan snapshots and owner-only status endpoints. Hosted functions cannot spawn and persist the llama.cpp binary. The daily discovery scan remains read-only.
- Hugging Face Spaces: documentation at https://huggingface.co/docs/hub/spaces-overview indicates static Spaces are available free, but creating a new Gradio/Docker compute Space requires a paid plan on a current free personal account. Even free CPU instances sleep when idle. No new hosting service was provisioned.
- Google Colab: prior free manual CPU inference worked, but it is not authorized as reliable unattended hosting.
- Local GitHub Actions: automatic runs were not enabled because private quota overage and billable minutes have not been independently excluded.
- Secure fallback: on-demand execution on temporary Linux with the pinned model and a bounded local SQLite queue; automatic remote code execution remains disabled. Queue leases and retries do not magically provide persistent compute.

### 7. Private dashboard verification

BountyForge v7 retains existing database-backed discovery and revenue information and adds a clearly labeled *historical Phase 3 evidence snapshot*, owner-only. The new status API is not an inference endpoint. It reports no continuous worker, no confirmed earnings, Qwen's 0/2 issue-specific attempts and the separate assistant-authored fix. The final user-facing claim must be based on live deployment readback, not merely a completed deploy response.

### 8. Commercial and security ledger

| Metric | Observed |
|---|---|
| Confirmed revenue | **$0** |
| Confirmed funded and eligible opportunities | **0** |
| Bounty submissions / external PRs | **0** |
| Paid AI inference calls | **0** |
| Additional paid infrastructure provisioned | **0** |
| Exact provider account charges | **Not independently audited** |
| Owner Mac access | **None** |
| Hostile-code security certification | **Not established** |

### 9. Remaining blockers

1. Independently verify hostile-repository sandboxing including cgroup enforcement, a stronger syscall allowlist, non-root host mapping, process accounting and third-party code supply-chain protections before broad external code execution.
2. Establish truly free, unattended, reliable CPU inference with enforceable zero-charge protection or continue owner-initiated on-demand runs.
3. Obtain a genuinely available, US-eligible, AI-permitted, no-fee and demonstrably payable Python bounty with explicit acceptance rules. Do not promote a stale marketplace label to verified escrow.
4. For the Boltons issue, check the entire pinned repository, upstream tests and edge cases before considering a public contribution. The attempted model solution **failed** this particular issue.
5. External PRs, bounty claims and payment arrangements require explicit owner approval.

**Phase 3 conclusion:** The isolated test runner, fail-closed funding classification and real upstream excerpt experiment advance the operator's engineering readiness. The first confirmed dollar remains **unearned**, and commercial autonomy is **not yet proven**.