# BountyForge revenue/Linus worker takeover, 2026-10-21 UTC

> Engineering evidence, not a statement of earned revenue or financial readiness.

## Primary goal and constraints

Turn the existing BountyForge repair infrastructure into a reliable **paid-first
software fulfillment operation**, able to work largely unattended on authorized
owned and eventually customer-supplied tasks. Additional purchases $0, no local
Mac, no Reddit acquisition, no paid inference without owner permission, no
outside offers/claims/submissions/payments without separately authorized gates.

Existing core architecture and draft PR #1 remain unchanged. This branch is
`engineering/revenue-linux-scout-20261021`, PR #2 targets the Phase 5
engineering branch, not main. All business-facing functionality stays in draft.

## Hosted evidence that must not be forgotten

- [39627486521](https://github.com/Ledgercorp/BountyForge/actions/runs/39627486521):
  first trusted PR offline standard Ubuntu acceptance, 9/9 scout tests, 8/8
  hosted Groq mock transport tests, evidence uploaded.
- [39627738050](https://github.com/Ledgercorp/BountyForge/actions/runs/39627738050):
  live standard Ubuntu GitHub search, 12 research leads and zero payable
  verification. The artifact contained 12 listings **all sourced from the
  Bounty Plaza aggregator**, including nonsensical astronomical amounts.
- [39628320803](https://github.com/Ledgercorp/BountyForge/actions/runs/39628320803):
  intentionally failing red TDD case, three source-quality failures.
- [39628556799](https://github.com/Ledgercorp/BountyForge/actions/runs/39628556799):
  green 12 scout + 8 hosted-model tests; live scan excluded 20 mirrored or
  otherwise unsuitable candidates. Remaining 12 were non-monetary lesson,
  annotation or bounty-index issues, with no advertised dollar amounts.
- [39628780253](https://github.com/Ledgercorp/BountyForge/actions/runs/39628780253):
  intentionally failing red TDD case for unpriced bounty labels.
- [39628929015](https://github.com/Ledgercorp/BountyForge/actions/runs/39628929015):
  green **13 scout + 8 hosted-model mock tests** on standard public Ubuntu.
  Live GitHub scan **zero monetary research leads**, zero verified payable
  candidates, zero paid-model calls and zero outside actions. This is a
  measured no-op commercial result, not an outage or earnings success.

All live results used the exact GitHub Actions event and built-in read-only
GitHub token. The original completed Phase 5 synthetic cycles, historical
five-case failures and durable state were not rewritten or rebranded.

## Current software on PR #2

- `bountyforge/revenue_scout.py`: three bounded GitHub issue searches, canonical
  URLs, duplicate suppression, literal Python language metadata, known mirror
  source rejection, generic aggregator metadata exclusion, absurd amount
  denial, mandatory advertised monetary amount, GET-only fixed origin,
  capped responses, read-only evidence without execution privileges.
- `tests/test_revenue_scout.py`: 13 negative/contract cases, all passed on
  hosted Ubuntu for commit `1f254789`.
- `bountyforge/groq_adapter.py`: opt-in Groq GPT-OSS 120B, fixed HTTPS
  endpoint and model, strict JSON schema, eight-call ceiling, no tool access,
  no redirects/proxies/retries, secret-safe errors.
- `tests/test_groq_adapter.py`: eight hosted/mock tests, no live model call.
- `.github/workflows/revenue-linux-scout.yml`: public standard Ubuntu, GH
  read-only permission. Trusted-PR runs live read-only research after offline
  tests; default-branch cron **not activated**.
- `.github/workflows/hosted-owned-canary.yml`: manual-only Groq owned-fixture
  evaluation, not run; requires secret and Free Plan attestation.
- `docs/GROQ_HOSTED_CANARY.md` and `docs/REVENUE_LINUX_WORKER.md`: bounded
  operating notes.

## Commercial conclusion

**Do not scale GitHub keyword searching or model inference on the current
unverified pool.** The first two live runs produced misleading leads; strict
sponsor/money/provenance gates now produce zero. Bounty Plaza advertises a
point-to-cash conversion, but there is no independent issue-specific sponsor
funding, eligibility, or payout attestation here. Opire's current documentation
states bounty creation/claim does not automatically trigger payment. An Algora
GitHub issue #262 reports a merged claim pending sponsor reward. Advertised
amounts and closed-loop agent activity are not sales.

Prioritize **customer orders with independently confirmed payment and clear
scope** as the primary BountyForge revenue path. Existing LeftSock paid service
funnels, a narrow Python bugfix offer, or other verified human customers are
better initial channels than speculative bounties. No payment processor has been
integrated here and no actual customer or order has been verified. Do not imply
that the paid-first service already exists.

## Exact next gates

1. Identify a customer acquisition channel that is permitted, measurable and
   affordable without new spend. Avoid assuming 12 GitHub labels are 12 buyers.
2. Add verified-order intake only when a trusted payment-provider receipt can
   be independently checked. Customer or model-provided `paid=true` is never
   a payment attestation. Do not authorize external code by a checkout flag.
3. Develop a narrow customer-approved Python deliverable contract and private
   artifact pipeline, maintaining separate execution and publication planes.
4. Configure `GROQ_API_KEY` only through GitHub Actions secrets after explicit
   owner Free Plan validation; the proposed held-out owned-fixture Linux
   benchmark has not run. Do not use larger paid runners or GPU Pods.
5. Compare GPT-OSS outputs to the frozen Qwen historical benchmark under the
   same allowed source and test scope before concluding model superiority.
6. For arbitrary third-party repositories, require dependency closure,
   hostile-source admission and security review, not just passing unit tests.
7. Perform independent code review, full repository regression and billable
   service/account checks before merging to main or activating cron.

## Tool constraint

Unblocked context/repository rule calls were attempted both before and after
implementation, but the connector reported that the account belongs to no
Unblocked organization and needs signup/create/join/reconnection. This is a
tool-access blocker, not a source-code or engineering-test failure.
Superpowers test-first/debugging and verification guidance was used with real
red/green GitHub Linux executions.
