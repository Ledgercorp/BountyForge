# LeftSock Labs | BountyForge Phase 4 execution report

October 20, 2026 | Local CPU engineering and commercial readiness | No new paid services

## Status

**Five historical real Python issues attempted; zero autonomous Qwen repairs passed.**
The benchmark was run against curated excerpts from the real Boltons `26.1.0` source,
not complete historical upstream checkouts. Each original defect was independently
reproduced before model repair attempts. None passed targeted tests after attempted
changes. **No approval-ready compensated submission exists. No revenue was earned.**

## Source and provenance

- Private repository: https://github.com/Ledgercorp/BountyForge
- Five historical issue references and exact GitHub source blob identifiers:
  `benchmarks/phase4/tasks/manifest.json`
- Source is modified only by clearly marked excerpt scaffolding and test harnesses.
  Boltons BSD-style copyright and license are retained in benchmark attribution.
- The existing Phase 3 sandbox prototype, prior receipts, private daily scanner and
  dashboard remain untouched unless specifically updated in this phase.

## New engineering

1. Added a deterministic AST-based model context selector in `bountyforge/context.py`.
   The selector uses explicit target function names, suppresses docstrings **only in
   model context**, carries referenced small top-level assignments through bounded
   dependencies, refuses ambiguous or missing functions and enforces a 3,200-byte
   default context budget. It does not execute input code.
2. Added `target_symbols` support to the existing minimal-edit path, so model context
   may be focused without rewriting the source file. The original complete file is
   still the exact-match patch validation target. A model cannot create new paths.
3. Added five curated historical Boltons tasks and a bounded local llama.cpp JSON
   patch benchmark runner. Baselines must fail for a reproducible reason before
   a model call is made; the only successful outcome requires tests to pass, with
   at least one test detected. Direct model writes to upstream repositories and
   external PR submissions remain impossible in this harness.
4. Added deterministic tests for context projection and the benchmark validator.

## Verification

- Context module's 7 new unit tests: **7 passed** on Python 3.13.
- Benchmark's 5 new validator/manifest tests: **5 passed** on Python 3.13.
- Historical baseline regressions: **all five reproduced** with expected failures.
- Qwen benchmark: **0 of 5 repaired**, 8 actual model requests,
  **423.67 seconds** combined benchmark wall times.
- Reported token usage (only responses that completed):
  1868 prompt and 518 completion tokens;
  timed-out requests do not report their full token consumption.
- Failure classes: {"JSONDecodeError": 2, "SyntaxError": 1, "ValueError": 1, "inference_unavailable_or_timeout": 2, "targeted_tests_failed": 2}.
- Two additional micro-prompt experiments on issue #460 completed in roughly
  22.54 and 25.2 seconds, but both still
  failed strict unique-old-text matching. They are *not* counted as a five-task repair success.
- The **complete existing private-repository test suite was not rerun in this execution**;
  the last proven full suite remains Phase 3's 61 passed with documented isolation
  conditions. Do not add 12 new unit tests to claim a new full-suite total.

### Actual autonomous model results

| Historical issue | Model calls | Failed checks | Outcome |
|---|---:|---|---|
| [#454](https://github.com/mahmoud/boltons/pull/454) | 1 | inference_unavailable_or_timeout | Failed |
| [#459](https://github.com/mahmoud/boltons/pull/459) | 2 | targeted_tests_failed, targeted_tests_failed | Failed |
| [#460](https://github.com/mahmoud/boltons/pull/460) | 1 | inference_unavailable_or_timeout | Failed |
| [#475](https://github.com/mahmoud/boltons/pull/475) | 2 | JSONDecodeError, JSONDecodeError | Failed |
| [#524](https://github.com/mahmoud/boltons/issues/524) | 2 | SyntaxError, ValueError | Failed |

**Measured improvement against Phase 3: none in repair success.** Phase 3 recorded
0/2 on issue #524; Phase 4 recorded 0/5 over five distinct historical issues
from one upstream repository. The smaller prompt reduced latency on a follow-up
but did not result in a validated repair. Broader generalization is unproven.

## Isolation and deployment boundary

The benchmark's subprocesses used unprivileged user, PID, network and mount
namespaces, a scrubbed environment, subprocess group termination and resource
limits. These particular subprocesses **did not chroot**. They ran only
manually curated, publicly attributable upstream excerpts, not hostile code or
complete dependency-rich Git checkouts. The existing separate Phase 3 opt-in
chroot/seccomp prototype retains its own seven recorded boundary tests.
Read-only cgroups and kernel-hardening uncertainty remain blockers to arbitrary
third-party execution. No untrusted third-party tests were enabled in the
production worker. No permanent or scheduled paid-risk model host was created.

## Bounty market screened

- [Algora highlight #8032](https://algora.io/highlight/bounties?status=open):
  **Tier B advertised $20**, original [GitHub issue](https://github.com/highlight/highlight/issues/8032)
  remains open but is SvelteKit documentation, has existing competing claims and
  lacks independently established US/AI/acceptance clearance. Not action-ready.
- [Opire claimant documentation](https://docs.opire.dev/rewards/pricing):
  payments are not automatic escrow. A creator reviews the PR and arranges
  payment independently. A GitHub issue claiming an Opire reward without current
  platform backing is Tier C until separately verified.
- [Nuclei issue #6674](https://github.com/projectdiscovery/nuclei/issues/6674)
  is closed despite older bounty listings. Excluded.

**Tier A verified funding: 0. Approval-ready paid submissions: 0.**
No claims, bidding, PRs, outreach, payment handling or financial commitments made.

## Cost and controls

- Paid AI inference API calls: **zero**.
- New paid infrastructure provisioned: **none**.
- Confirmed bounty revenue: **$0**.
- Exact provider billing totals have **not** been independently audited.
- Model hosting remains ephemeral. Running a model on this temporary Linux
  worker is not an unattended free cloud hosting guarantee.

## Next engineering decision

The tested 1.5B model is **below the evidence threshold for autonomous paid fixes**.
Do not permit external submission or unsolicited third-party execution. Before
attempting paid work, independently compare a better-suited open-weight model
on the same five pinned fixtures with free CPU resources and safe limits, or
retain the existing model for limited triage only. Full historical upstream
suite acceptance and paid-reward eligibility remain separate requirements.