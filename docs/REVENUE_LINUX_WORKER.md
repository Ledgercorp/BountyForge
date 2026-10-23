# BountyForge revenue scouting Linux worker

## Stage 1 scope

This is a read-only, bounded research worker, not a functioning earnings
system or an independently certified malicious-code sandbox.

It uses the standard public-repository GitHub Actions Ubuntu runner and the
built-in read-only GitHub token. It does not provision GPUs or other compute,
call AI APIs, install third-party code, run external repositories, submit PRs,
claim bounties, send messages, transfer funds or access the owner's Mac.

Three bounded public GitHub issue searches look for open Python-repository
reward leads. Each candidate is ranked for **research only**. An issue's
advertised dollar amount is never independent proof of funds, permission to
participate or expected payment. All qualified, approved, executed, submitted
and paid counts stay zero until future independently verified stages.

## Operating and cost limits

* Workflow: .github/workflows/revenue-linux-scout.yml.
* Python module: bountyforge/revenue_scout.py.
* Safety tests: tests/test_revenue_scout.py.
* Linux runner: standard ubuntu-24.04, 6-minute job timeout.
* API access: GET only to fixed GitHub Search and repository metadata paths.
* Limits: three searches, 20 issues per search, 12 candidates verified for
  Python primary language, 256 KB per API response, 12-second network timeout.
* Artifacts: sanitized JSON research leads, retained for two days.
* Failure policy: if Github search fails, fail closed instead of reporting
  that no opportunities exist.
* No workflow schedule. Push/PR checks use offline fixtures; live research
  requires an explicit manual selection. No repeated searches were needed by
  the integration review.
* Incomplete Search responses fail closed. Metadata-budget exhaustion reports
  an incomplete observation and the number of unexamined candidates, distinct
  from a completed bounded sample with zero prospects.
* Standard GitHub-hosted Linux runners are listed as free for public repos.
  Account billing settings and storage invoices have not been independently
  audited. No spending is authorized.

## Why this is the first stage

The earlier BountyForge evidence examined 33 leads and qualified none for
safe paid Python repairs. Inference before sponsor/payout verification risks
wasting model quota on false positives. Opire's documentation makes clear
that creating/claiming a bounty does not automatically pay a contributor:
the sponsor must approve and arrange payment.

This source is a bounded acquisition filter. It does not solve the commercial
verification problem by itself.

## Run offline without secrets

    python -m unittest discover -s tests -p test_revenue_scout.py -v
    python -m bountyforge.revenue_scout --mode offline --output /tmp/revenue.json

To investigate live source data, pass --mode live and optionally a read-only
GitHub token in GITHUB_TOKEN. Never put keys in output, command arguments or
commit history.

## Next development gates

1. Establish sponsor-controlled reward/funding evidence and payout terms,
   availability, US eligibility, identity requirements and AI-use permission.
2. Expand the admitted task profile beyond tiny single-line Python repairs only
   after reproducible tests and isolation evidence prove safe execution.
3. Benchmark an authorized stronger coding model on frozen fixtures. Keep keys
   in scoped secrets, and do not turn a free tier into a billable API silently.
4. Once real paid candidates exist, allow bounded drafts and independent
   verification. Any outside message, offer, claim, PR, contract or payment
   action still needs owner authorization.

The production branch, original engineering PR, existing durable ledger,
and current model worker were not changed by this feature.
