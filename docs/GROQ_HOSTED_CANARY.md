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
   The default `suite=structural` uses the same frozen owned cases as the
   Qwen study. `suite=original` explicitly selects the earlier four simpler
   owned tasks. Both choices use v5 and retain the eight-call ceiling.

## Test and execution behavior

- Push checks are **offline mocked tests only**; no model key is supplied.
- Both inference workflows share `bountyforge-repair-worker` concurrency with
  the existing repair workflows. The revenue scout has no recurring schedule;
  push and PR smoke checks are offline, and live research requires a manual
  `scan_mode=live` dispatch.
- Manually enabled job uses standard public Ubuntu, read-only repo permission,
  pinned Docker, a 20-minute timeout and **at most eight** model calls.
- Checkout, Python setup, image pull and an independent Docker admission
  preflight run before the inference step receives `GROQ_API_KEY`. The key is
  step-scoped. The test container still receives only the existing explicit
  nonsecret environment whitelist, without the model credential or GitHub token.
- Request origin and model ID are fixed in code. Redirects, proxies and
  automatic provider fallback are denied. Prompts and responses are bounded.
- The evaluated fixtures are the selected four SHA-pinned owned development
  tasks, with structural cases selected by default. They are not historical
  Boltons benchmarks or commercial source. The existing
  line validator and owned-test Docker admission remain mandatory.
- Reports may contain owned fixture source, prompts and model responses. Treat
  artifacts as public research evidence, never feed confidential source to
  the free API or report.
- A passing model response is **not** a passing coding task. Successful repair
  requires the existing independently run tests and later reviews.
- `scripts/validate_owned_canary.py` independently checks the exact revision,
  selected task identities, source/test hashes, Docker proofs, all four
  reproduced baselines, completed task states, response hashes, model identity,
  token accounting, call numbering and timing totals. Transport failures,
  missing baselines or any blocked task fail the workflow. A complete experiment
  with zero passing repairs remains valid evidence and is reported as zero;
  the gate does not require a manufactured success rate.
- A separate step without the provider credential reconstructs every reported
  success through the source validator, matches its exact patch, proves fresh
  Docker admission and reruns the frozen tests. Its report binds the input SHA
  and performs zero inference. A failed replay prevents a successful canary.
- The model cannot access GitHub write tokens, claim bounties, publish source
  or perform payments. No test task, executable or MCP server from a third
  party is admitted by this workflow.

## Known limits

The manual canary now explicitly selects a **1,024-token total generation cap**
with low reasoning effort and reasoning omitted from retained messages. This is
an opt-in constructor setting, separate from the unchanged 150-token patch-interface
limit, 3,000-byte final response cap and source validators. The default adapter
remains at the earlier total limit. Eight requests allow at most 8,192 generated
tokens plus bounded prompts; the canary spaces requests at least 60 seconds apart.
Quota errors stop the instance; there are no retries or automatic fallback. This
configuration is staged and mocked-tested, not a live inference result or a Free
Plan verification. It still requires the account/key/owner gates above.

The adapter fits only BountyForge's small `complete_line` and
`complete_diagnosis` interfaces; the live canary selects v5 only. Its eight-call
ceiling does not cover a full sixteen-call v6 comparison. It is not a general
agent or a complete paid-gig delivery engine. The small patch profile and bounded
reasoning allowance may be insufficient for complex repairs. Larger contexts or autonomous tool use
must be separately reviewed. Commercial qualification still returns blocked
without independently verified sponsor funding, payout terms, AI permission,
eligible scope and secure reproduction.

## Status

- Adapter and mocked tests are committed on the revenue Linux feature branch.
- Baseline full-repository CI was independently verified at
  `1f2833581ca6f9d96a0406c7c0a40dc9320cb3ba` in
  [run 39635335310](https://github.com/Ledgercorp/BountyForge/actions/runs/39635335310),
  job `119344157270`: 246 cases executed, 239 passed and seven skipped.
  This establishes regression success at that source, not live Groq acceptance.
- The new workflow/evidence-gate changes require their own regression result.
  No model dispatch is needed for those offline checks.
- No Groq credentials configured through this work, no live Groq requests, no
  spending, no commercial reviews, no outside submissions.

Provider billing remains independently unverified. The Free Plan variable is
an owner assertion, not a financial kill switch; the validation report explicitly
keeps `billing_independently_verified=false`. No live canary should be dispatched
until the selected credential's current Free Plan and applicable terms are
verified and that particular evaluation is authorized.
