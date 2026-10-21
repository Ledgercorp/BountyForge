# BountyForge bounded autonomy runbook

Current status: NOT_READY for unattended paid bounty repairs. Changes are on a feature branch, not deployed.

## Verified engineering
- The existing Hatchable owner-private scanner is active and saved 25 read-only candidate records at 12:00 UTC October 20, 2026.
- New Python evidence controller passed nine isolated local unit tests.
- Qwen2.5-Coder 1.5B and llama.cpp b11750 archives passed SHA-256 verification in Linux.
- Loopback inference returned a correct JSON line edit in 5.96 seconds during a controlled sample.
- The Linux bootstrap rejected a bad runtime digest and disallowed port.
- No hosted GitHub Actions run, complete regression suite, new five-case benchmark or real paid repair has been verified by this branch.

## Files
- bountyforge/autonomy.py: fail-closed commercial status, digest-addressed evidence, sanitized synthetic-only canary and exclusive file writes.
- scripts/autonomous_cycle.py: offline or read-only live issue scan, optional owned synthetic addition canary, no upstream code execution.
- scripts/validate_evidence.py: separate schema and evidence digest validation.
- scripts/bootstrap_actions_inference.sh: verified model and runtime, loopback-only server.
- .github/workflows/autonomous-dry-run.yml: manual-only tests and scan.
- .github/workflows/manual-cpu-canary.yml: manual-only CPU model acceptance with default unverified billing acknowledgement.

## Manual Linux validation commands
python -m unittest discover -s tests -v
python -m unittest discover -s benchmarks/phase4 -v
mkdir -p evidence-run
python -m scripts.autonomous_cycle --scan offline --output evidence-run/cycle.json
python -m scripts.validate_evidence evidence-run/cycle.json
bash scripts/bootstrap_actions_inference.sh --verify-only

An optional --canary switch uses the existing auto_line repair worker only on fixtures/controlled/addition with already-running numeric-loopback Qwen.

## Required acceptance gates
1. Run all repository tests and original five-case model benchmark on current code; distinguish correct repairs from rejection.
2. Independently verify GitHub billing zero-overage controls before triggering Actions at scale or enabling a cron schedule.
3. Prove Actions CPU cold/warm inference, resource use, verified hashes and repeatable canary output.
4. Prove stronger hostile-code containment before executing any third-party checkout. Current namespace prototype is uncertified.
5. Design durable idempotent coordination across disposable jobs. Artifacts alone are not a durable concurrent queue.
6. Independently verify funding, US participation eligibility, AI policy, payment rules and authorization for each real issue.
7. Keep public PR submission, reward claims and any payment/contractual action behind explicit owner approval.

No scheduled repairs, OCI provisioning, paid inference, Mac access, external PRs, modifications to unrelated projects or new spending were authorized or performed in this branch.
Confirmed bounty revenue: $0.
