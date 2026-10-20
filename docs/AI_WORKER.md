# BountyForge AI Worker: development acceptance

State: bounded local-model proposal pipeline implemented; **real model inference NOT yet run**.

## Constraints

- No additional spending, paid inference endpoints or paid compute.
- Do not use the owner's Mac.
- Do not auto-claim bounties, comment on issues, fork or modify external repositories, run untrusted generated code, or submit pull requests.
- Monetary amounts from GitHub Search are **unverified**, not earning estimates.
- All source snippets and issue descriptions passed to the model are untrusted data, never instructions.

## How to run when a free Linux host is available

1. Obtain a trusted llama.cpp Linux binary, then run \`bash scripts/start_local_model.sh\` **only** after confirming sufficient disk, memory and network quotas. The downloader verifies the official SHA-256. This action is not performed by the hosted Hatchable dashboard.
2. Have a legitimate candidate from \`python -m bountyforge.cli scan\`.
3. Independently verify that the task is actually paid and available, and that AI-assisted contributions are permitted.
4. Inspect a disposable **read-only** checkout of the source in a trusted isolated Linux workspace.
5. Run an explicit, bounded proposal:

\`\`\`bash
python -m bountyforge.run_draft \
  --report dashboard/data/results.json \
  --issue https://github.com/OWNER/REPO/issues/NUMBER \
  --workspace /tmp/review-only-checkout \
  --file src/approved.py \
  --output reports/issue-NUMBER-draft.json
\`\`\`

Only the **report JSON** is written, outside the checkout. The model can propose changes only to existing allowlisted files (max 3 source snapshots / max 5 patch entries). The worker checks Python and JSON syntax, path traversal, symlink escapes, size, no-op changes and unexpected JSON fields. It generates unified diffs for human review. It **does not** run the generated program, any shell command, or tests from the issue.

## What is verified

- 12 patch-staging unit tests passed in an isolated Linux workspace.
- 5 worker unit tests passed using a deterministic **fake model**.
- The hosted GitHub scanner operates independently, and no remote paid AI credentials are used.
- The model file's published SHA-256 is \`cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046\`, verified against Hugging Face metadata, but the model bytes could not be downloaded in the current network-isolated Linux execution environment.

## Remaining evidence

- Run one real Qwen inference on a verified free Linux host with the exact pinned model.
- Independently test the worker's local HTTP client against that running server.
- Obtain a true disposable execution sandbox with filesystem and network isolation before enabling code tests on generated proposals.
- Prove the first actual funded bounty and its terms before attempting any outside claim or submission.

**No code execution performed. No bounty application or payout initiated. No paid usage.**
