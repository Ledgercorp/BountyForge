# Hosted GPT-OSS on standard GitHub Linux: gated evaluation

## Purpose

Evaluate whether a more capable remote coding model can solve BountyForge's
already-owned and SHA-pinned Python development fixtures. This does not
authorize arbitrary downloaded repositories, jobs submitted to outside
maintainers, paid API usage, or deployment.

Files: `bountyforge/groq_adapter.py`,
`tests/test_groq_adapter.py`,
`.github/workflows/hosted-owned-canary.yml`.

## Why Groq

Groq currently offers `openai/gpt-oss-120b` with structured JSON-schema
responses. Its Free Plan has rate limits, and requests above those limits
receive 429 rather than an automatic charge, **provided the account actually
remains on the Free Plan**. External usage eligibility and the user's current
plan have not been verified. This experiment has made **zero live Groq calls**.

Official references

- https://console.groq.com/docs/model/openai/gpt-oss-120b
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/rate-limits
- https://community.groq.com/t/do-i-get-charged-for-anything-on-the-groq-free-plan/832

## Preconditions to run the live canary

1. User verifies the Groq account **is currently on the Free Plan**, has no
   automatic paid-tier usage and meets the provider terms. Do not attest
   without verification. Usage estimates may appear in the dashboard.
2. Place a Groq API key in GitHub Actions secret `GROQ_API_KEY`. Never put the
   credential in a repository file or GitHub Actions input.
3. After verifying Free Plan status, set repository variable
   `BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED` to `1`. Remove it if the plan
   changes. This is a human assertion, **not** an independent billing
   kill switch.
4. Manually dispatch `hosted-owned-canary.yml` with `run_live=true` from
   the specifically approved engineering branch once GitHub has registered
   the workflow. Workflows defined only on a feature branch may not appear
   under the workflow_dispatch UI until a safe default-branch registration.
   Do not merge the existing broad engineering PR merely to unlock the UI.

## Test and execution behavior

- Push checks are **offline mocked tests only**; no model key is supplied.
- Manually enabled job uses standard public Ubuntu, read-only repo permission,
  pinned Docker, a 20-minute timeout and **at most eight** model calls.
- Request origin and model ID are fixed in code. Redirects, proxies and
  automatic provider fallback are denied. Prompts and responses are bounded.
- The evaluated fixtures are the existing four owned development tasks, not
  historical Boltons benchmarks and not commercial source. The existing
  line validator and owned-test Docker admission remain mandatory.
- Reports may contain owned fixture source, prompts and model responses. Treat
  artifacts as public research evidence, never feed confidential source to
  the free API or report.
- A passing model response is **not** a passing coding task. Successful repair
  requires the existing independently run tests and later reviews.
- The model cannot access GitHub write tokens, claim bounties, publish source
  or perform payments. No test task, executable or MCP server from a third
  party is admitted by this workflow.

## Known limits

The adapter fits only BountyForge's small `complete_line` and
`complete_diagnosis` interfaces; it is not a general agent or a complete
paid-gig delivery engine. Eight calls and 150 completion tokens each may be
insufficient for complex reasoning. Larger contexts or autonomous tool use
must be separately reviewed. Commercial qualification still returns blocked
without independently verified sponsor funding, payout terms, AI permission,
eligible scope and secure reproduction.

## Status

- Adapter and mocked tests are committed on the revenue Linux feature branch.
- Offline unit tests have been executed independently in a Python scratch
  harness, with the production `LINE_SCHEMA` interface mirrored for isolation.
- Full-repository hosted CI outcome is not independently established.
- No Groq credentials configured through this work, no live Groq requests, no
  spending, no commercial reviews, no outside submissions.
