# Groq credentialed owned-canary acceptance attempt, 2026-10-21

## Exact outcome

This experiment was started only after the owner configured a GitHub Actions
`GROQ_API_KEY` repository secret and attested that the account was on the
Groq Free Plan via `BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED=1`.

The private key was never fetched or printed. GitHub's masked job environment
reported `GROQ_API_KEY: ***` and an accepted attestation value `1`.
These checks establish **configuration presence**, not independently certified
Groq billing status, secret validity or model permission.

- First authorized branch-only canary:
  [39645988469](https://github.com/Ledgercorp/BountyForge/actions/runs/39645988469)
  (head `4084ea314d1073e0d42b49172290ac19a3a2e592`).
  Owned structural `ast_contract_v5`, one attempted Groq request, zero model
  results, zero verified fixes, three unattempted cases blocked.
  The original adapter intentionally masked the underlying cause as a general
  provider failure. The complete canary failed acceptance as required.
  Archived Actions artifact ID `12367830523`; ZIP SHA-256
  `cd9881bd3601214c658f545a2c07c5a6dbdf970966efa588d5530bd699ad03a3`.
- A fail-closed diagnostic change classified only numeric HTTP response status,
  still suppressing provider error bodies, request headers, raw model output
  and credentials. Its new negative tests first failed on hosted Linux.
  Commit `6894853c0b8b12583a97f337b954490cd6ec0915` then passed
  [hosted run 39646500191](https://github.com/Ledgercorp/BountyForge/actions/runs/39646500191):
  **295 tests executed, 288 passed, seven existing rootfs skips**.
- Second and final controlled branch-only canary:
  [39646633511](https://github.com/Ledgercorp/BountyForge/actions/runs/39646633511)
  (head `74d4ebfd1406e25a6b005da295c7225dca04d06c`).
  Safe offline tests and immutable Docker preflight succeeded; Groq returned
  **HTTP 403 Forbidden** on the *first* inference request (roughly 0.1 s).
  The model adapter stopped, no additional requests or tests executed,
  `attempted=1`, `passed=0`. The authoritative retained result says
  `Hosted inference unavailable or rejected (http_403); no retry or fallback`.
  Actions artifact ID `12367223243`; ZIP SHA-256
  `f5a861a99363a086124481264d5fd2e10168abda620648dc2bad1408e1021477`.
- Both one-time feature-branch push overrides were **removed** after use,
  returning `.github/workflows/hosted-owned-canary.yml` to its original
  manual-only requirement. No recurring model evaluation is active.

## Interpretation, not speculation

Groq's official [HTTP errors](https://console.groq.com/docs/errors)
document 403 as permission restrictions. Its
[model-permission policy](https://console.groq.com/docs/model-permissions)
explicitly returns HTTP 403 when a model is blocked by organization or
project-level restrictions. This is the first concrete owner-side setting to
check; however, **HTTP status alone does not prove the exact policy code**.
The provider error body was purposefully never logged, and the API key was not
retrieved. The event was **not** a verified model-quality failure and must not
be ranked against the existing Qwen v5/v6 benchmarks.

A rate-limit rejection would normally return 429, not 403. A normal invalid
authentication response is 401, not 403. Neither conclusion establishes
billing/permissions positively.

## Next owner-side action before another request

In the authenticated Groq Console, check
[organization model limits](https://console.groq.com/settings/limits)
and, if using a project,
[project model permissions](https://console.groq.com/settings/project/limits).
Ensure exact `openai/gpt-oss-120b` is allowed in *both* scopes, or that
neither scope blocks it. Project restrictions cannot override organization
blocks. Confirm the API key belongs to the selected project, that project
still shows Free Plan and unused quota, and that no paid billing is enabled.

Do not paste the API key, authorization headers, raw error body, payment
data or customer source into a conversation or GitHub issue. The owner may
describe the permission controls in plain words, without screenshots of keys.

Do **not** rerun the live benchmark until the permission state is checked;
the model remains unadmitted. If the owner confirms permissions but 403
persists, implement a separately authorized, secret-safe `GET /models`
metadata diagnostic (no inference) or consult Groq support.

## Protected boundaries

Zero customer source, outside code execution, commercial contracts, payments,
third-party claims, external submissions or production deployments.
Main, draft PR #1, dashboard v11 and the synthetic ledger were not changed.
The canary's failure was correctly fail-closed and its evidence retained.
