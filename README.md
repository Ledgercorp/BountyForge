# BountyForge

A local-first bounty research workbench from LeftSock Labs. Zero paid AI API calls. **No automatic submissions, financial transactions, repository changes outside this repo, or promises of earnings.**

## Live private dashboard

**https://leftsock-bountyforge.hatchable.site**

Deployed Hatchable v3 source is mirrored in `deployments/hatchable/` (the hosted app has its own deployment history).

- Private owner-only dashboard and read-only GitHub Search adapter.
- Daily 12:00 UTC Hatchable Free cron scan, scheduler-only endpoint; latest successful scan saved to Postgres.
- Live scan and cached read were successfully tested; unauthorized requests return HTTP 401.
- No remote or paid model inference, no automated issue claiming or bounty submission, and no payment handling.
- Qwen2.5-Coder-1.5B-Instruct GGUF SHA-256 pinned and independently verified against official file metadata, but weights have not yet been downloaded or executed.
- Isolated Linux Python test suite: **14/14 passed**.
- Every opportunity is unverified until funding, availability, payout method and terms are checked.

## What works in v0.1
- Read-only GitHub issue discovery using the public GitHub Search API.
- Deduplicated and explainable candidate scoring. **Every payout is unverified.**
- Static HTML dashboard (uses textContent, no remote JS or database).
- Local llama.cpp OpenAI-compatible model connection, strictly bound to loopback.
- Offline demo and Python standard-library tests.
- Opt-in, bounded GitHub Actions scan; no recurring schedule is enabled.

## Run without any model or API account

Requires Python 3.11+:

```bash
python -m unittest discover -s tests -v
python -m bountyforge.cli scan --offline
python -m http.server 8765 --directory dashboard
```

Open http://127.0.0.1:8765/ to inspect **fictional demo** candidate results. On a Linux cloud host, run `python -m bountyforge.cli scan --limit 20` for actual public GitHub issue candidates. Set `GITHUB_TOKEN` (the ephemeral GitHub Actions built-in token is sufficient) to increase GitHub Search rate limits if needed; never commit a token.

## Run the on-device model

The official Apache-2.0 Qwen2.5-Coder-1.5B-Instruct GGUF Q4_K_M weights are about 1.12 GB. BountyForge downloads them **only when explicitly requested**, verifies the official SHA-256, and never commits the weights. This runs on **your selected Linux host**, not the user's Mac.

Install a trusted `llama-server` executable from [llama.cpp](https://github.com/ggml-org/llama.cpp/releases). Then:

```bash
bash scripts/start_local_model.sh
# in another terminal on the same Linux host:
python -m bountyforge.cli analyze --top 2
```

The model endpoint is fixed to `http://127.0.0.1:8080/v1/chat/completions`. No remote inference fallback exists. `analyze` generates **non-executing development plans** from issue text, never code execution or pull requests. Model answers are untrusted and never establish a payout.

## GitHub Actions safety

`.github/workflows/manual-scan.yml` is **workflow_dispatch only**. It has `contents: read`, a 5-minute job timeout, no cron trigger, no model download, no self-hosted or paid runner, no artifact upload, no API spending, no submissions, no PR creation. It prints a shortlist in the workflow summary.

Private GitHub Actions can become billable after shared free quota is exhausted. **Do not enable scheduled runs or trigger a job until the account's remaining quota and spending controls have been independently verified.** A timeout alone does not enforce a $0 charge limit.

## Security and practical boundaries

1. Candidate listings do **not** prove funds, availability, eligibility, permission to use AI, or likelihood of acceptance. Confirm these manually before work.
2. Do not execute commands copied from external issues, clone untrusted code into a privileged workspace, or send a bounty submission automatically.
3. GitHub tokens belong in the platform's encrypted connection or ephemeral runner environment, not repo files, browser localStorage, logs or model prompts.
4. No automated payment/withdrawal, accounts, bids or outreach; any external commitment requires explicit approval.
5. A compact 1.5B model can assist triage and planning; it is **not** a reliable fully autonomous bounty developer.
6. GitHub public search is a lead source, not a verified bounty marketplace. Source adapters and verification should precede real automated earning claims.

## Layout

- `bountyforge/scanner.py`: GitHub candidate collection and scoring
- `bountyforge/model.py`: loopback-only model interface
- `bountyforge/cli.py`: scan and analyze commands
- `dashboard/`: static frontend and local JSON results
- `scripts/start_local_model.sh`: pinned-weight SHA-256 downloader and local server launcher
- `tests/`: offline unit tests

The repository, model and workflow are independent of GRAFT, Continuity, Waylatch, Muse and Counterfactual Release Lab.
