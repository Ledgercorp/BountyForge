# Phase 26 — Real bounty discovery and pilot readiness

Date: 2026-10-26
Base: `4687c57034ae2f82253c8f7a3a44734fa7a59f8d`
Branch: `engineering/phase26-real-bounty-pilot-20261026`
Commercial admission: **NOT_ADMITTED**
DeepSeek authorization: **CLOSED; no Phase 26 inference authorized**

## Outcome

The Phase25 discovery path could not return Superteam records because its
documented agent feed returned HTTP 401. This phase established a working,
unauthenticated, read-only GitHub Search API source and a targeted query for
open Python issues commented on by Algora's official GitHub bot. The search
source is explicitly a lead generator: it is capped at three records per query,
does not claim to scan the whole market, retains issue-body hashes rather than
untrusted body text, and cannot create a claim, authorize execution, or infer
that a reward is funded. The official GitHub REST documentation permits public
unauthenticated reads and describes the separate rate limits for search; the
adapter records rate-limit headers, bounds responses to 256 KB, has a 15-second
deadline, refuses redirects, sends no credentials, and makes no more than ten
requests per client instance. See the [GitHub Search REST API](https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests)
and [GitHub REST rate-limit guidance](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

The live scan on 2026-10-26 received HTTP 200 from both GitHub searches. The
broad fixed query reported 14,790 matching issues and returned only three
recent matches; the Algora-bot query reported eight and returned three. Search
metadata marked neither response incomplete, but BountyForge deliberately
reports both scans as non-exhaustive because it requests only page one. The
Superteam request returned HTTP 401 and Coinbase's SOL ticker returned a
momentary $101.40 quote; Coinbase returned HTTP 404 for USDC-USD. This is a
market observation, not a bounty valuation or withdrawal route. The sanitized
receipt records source URLs, observation time, response hashes, issue IDs,
claim labels, body hashes, and conservative qualification reasons without
publishing issue bodies: [live discovery evidence](../evidence/phase26/live_discovery_2026-10-26.json).

No reviewed opportunity passed all required gates. The closest live listing
was a $15 USD Flyde reward displayed as open on Algora, but the issue is a
VS Code/TypeScript extension task, the repository root license was not found
in the checked location, at least seven competing open PRs propose the same
issue, and AI-agent participation, U.S. eligibility, source/test rights,
upfront costs, and the owner's payout route remain unknown. It is not a
commercial pilot candidate for the current Python-only, hostile-code-not-admitted
worker. A complete, machine-readable decision ledger is at
[opportunity assessment](../evidence/phase26/opportunity_assessment.json).

## Provider findings

**Superteam Earn.** The endpoint in the existing adapter is the documented
`GET /api/agents/listings/live?take=20` route; 401 is expected without the
agent API key. Superteam's official [agent guide](https://superteam.fun/earn/agents)
says the owner must register an agent to receive that key and a claim code,
only listings with `AGENT_ALLOWED` or `AGENT_ONLY` permit agent submissions,
and a human must claim payout after an award. This assignment did not create
an agent, retrieve an API key, submit work, or attempt any other route. Owner
setup is required before BountyForge can read that feed; U.S. eligibility and
the eventual payout path must still be checked on each listing and by the
human account holder.

**Algora.** GitHub's public Search API can identify issues with comments from
`algora-pbc[bot]`, but those comments and issue labels alone do not prove that
a bounty remains available or that a payment will be made. Current first-party
examples exposed an awarded OpenFGA bounty and old/contested offers. Algora's
[public API documentation index](https://api.docs.algora.io/) describes bounty
query/create/update/delete capabilities, but the documentation host returned
HTTP 503 when its route details were checked; no undocumented endpoint was
called. The current [Algora Terms of Service](https://algora.io/terms) prohibit
automated website monitoring/copying without prior written consent. Therefore
Phase26 adds no Algora website scraper and does not schedule Algora page
retrieval. A documented, permitted API route and its authorization rules must
be established before automation is added. Algora pages call payouts “cash
awards,” but these sources did not verify account acceptance, payment rail,
U.S. eligibility, escrow, or the owner's withdrawal setup.

**Opire.** Its current [pricing/payment documentation](https://docs.opire.dev/rewards/pricing)
says bounty creators review the submitted PR and arrange payment directly;
claiming a listing does not trigger an automatic payment. Its [lifecycle
documentation](https://docs.opire.dev/rewards/lifecycle) says code owners
create bounties on their own repository issues. No documented public listing
API or current, eligible and funded Python task was established, so BountyForge
did not invent a route or scrape the site. Any Opire match requires its issue
terms, creator/payer, AI permission, location, source rights and direct payment
commitment to be verified independently.

**OnlyDust.** The platform's [current vision](https://docs.onlydust.com/overview/vision-and-roadmap)
states that it serves human contributors and describes AI collaboration as
human-led. No specific program authorizing an autonomous coding agent was
verified. No OnlyDust task was treated as agent-eligible or payable in this
phase. A human contributor's permitted use of AI is not equivalent to
authorization for BountyForge to participate as an agent.

## Ranked candidate decisions

1. **Flyde #112 — $15 USD displayed as open.** The [Algora Flyde board](https://algora.io/flydelabs/bounties?status=open)
   displayed one open $15 task for `flyde#112`; the [GitHub issue](https://github.com/flydelabs/flyde/issues/112)
   remained open and was updated on 2026-10-25. The board text labels the reward
   as a cash reward; a funded escrow or guaranteed payout was not established.
   [PRs #293, #292, #291, #286, #285, #283 and #282](https://github.com/flydelabs/flyde/pull/293)
   are open competing attempts or duplicates. This is the closest observed live
   task, but it fails BountyForge's supported-language profile and all of AI,
   U.S., rights, and payout verification. No source or tests were fetched or
   executed.

2. **Toingg Jarvis #13 — $5 USD claim.** The [issue](https://github.com/PG-AGI/toingg-jarvis/issues/13)
   is open and an [Algora bot comment](https://github.com/PG-AGI/toingg-jarvis/issues/13#issuecomment-4598764661)
   advertised $5. The requested work spans Windows, Linux and macOS installers.
   [PR #89](https://github.com/PG-AGI/toingg-jarvis/pull/89) and [PR #92](https://github.com/PG-AGI/toingg-jarvis/pull/92)
   are both open and claim the issue. Current Algora-board status, payout
   mechanics, U.S. eligibility, AI eligibility and source/test rights remain
   unknown. It is both contested and outside the current bounded Python profile.

3. **Onyx #2281 — $250 USD claim, already claimed/uncertain.** An [Algora bot
   comment](https://github.com/onyx-dot-app/onyx/issues/2281#issuecomment-2322605615)
   records a $250 bounty; a later [bot comment records a PR claiming it](https://github.com/onyx-dot-app/onyx/issues/2281#issuecomment-2464839836).
   The GitHub issue remains open with 170 comments and further claims. The
   current [Onyx Algora page](https://algora.io/onyx-dot-app/bounties?status=open)
   presents completed bounties, not this task as open. Current availability,
   payout, U.S. and AI eligibility are unresolved; a connector feature is not a
   narrow repair. Do not attempt it.

4. **OPAL #661 — $1,500 USD, awarded.** The [Algora bot recorded an award](https://github.com/permitio/opal/issues/661#issuecomment-2561888171)
   and the [Permit.io Algora board](https://algora.io/Permitio/bounties?status=open)
   currently reports zero open and eighteen completed bounties. Although the
   repository has an Apache-2.0 license, the OpenFGA policy-store feature is
   broad and already has claimed PRs. It is unavailable, not a pilot.

5. **oss-hunter-livefire #1 — apparent $50, quarantined.** The [issue](https://github.com/tine1117/oss-hunter-livefire/issues/1)
   has a `$50` label and remains open, but the repository's [README](https://github.com/tine1117/oss-hunter-livefire/blob/main/README.md)
   explicitly calls it a sandbox/test fixture and requests contributors star
   the repository and follow the owner. The issue has 72 comments and numerous
   duplicate PRs. No independent funding or real production task was verified.

6. **BasedHardware Omi #23328 — $50 proposed, not funded.** The [issue](https://github.com/BasedHardware/omi/issues/23328)
   describes a proposed bounty. No funding, payer commitment, or payment terms
   were independently verified.

Exact evidence fields and decision reasons appear in `opportunity_assessment.json`.
The live search's three broad candidates also contained non-actionable
coordination/testbed issues; those remain quarantined as search leads, not
commercial offers.

## Pilot plan, cost and payment

There is no selected commercial pilot and no third-party source/test revision
has been admitted. BountyForge therefore prepared no repair prompts, source
checkout, dependency execution, test execution, external PR draft, claim, or
paid inference plan. Phase22's DeepSeek spending grant remains closed. No
DeepSeek key was retrieved, no request was made, and no credit ledger or STOP
marker was changed. A future paid plan must be tied to an exact, eligible task
and receive a new owner authorization with a model, request/token ceilings,
cost reserve and independent replay criteria. Current pricing/credits are not
assumed.

No wallet, financial account, or payout profile was created or inspected. The
Flyde reward is quoted in USD on Algora, but no owner account eligibility,
Stripe/payout route, fees, withdrawal qualification, or payment proof was
verified. Coinbase's SOL quote does not establish spendable liquidity for this
owner; its USDC market endpoint returned 404. Earnings remain **$0**. The
ledger preserves discovery, submission, award and received funds as separate
states, and no simulated receipt is reported as revenue.

## Security and acceptance gaps

The GitHub discovery adapter is model-free, uses fixed HTTPS origins and fixed
queries, sends no GitHub credential, does not follow redirects, caps search
results at three and response bytes at 256,000, records public response hashes,
and drops issue body text after hashing it. Advertised issue text, comments,
labels and reward amounts remain untrusted. A search match never means funded,
AI-authorized, U.S.-eligible, source-authorized or safe to execute.

The existing hostile-code admission remains **NOT_ADMITTED**. No third-party
checkout, build, dependency install, or tests ran. Existing sandbox testing
covers owned fixtures only; package lifecycle scripts and malicious build/test
commands remain an unresolved boundary. The nine historical namespace/rootfs
CI skips remain skips, not passes. Payment review, owner approval, and delivery
remain separate gates.

## Test and action record

* Focused discovery, normalization and CLI tests: 27 passed after fixing
  test-seam issues during development (the final run is recorded below).
* Live read-only calls: fixed GitHub Search queries, Superteam listing GET,
  Coinbase SOL and USDC public tickers. No external writes, accounts, source
  execution, DeepSeek requests, submissions or payment operations.
* Additional spending: `$0`; confirmed earnings: `$0`.
* No production changes; no existing PR or `main` branch was modified.

## Local acceptance completed

The offline-built Linux rootfs enabled all eight existing namespace/rootfs
checks on this Linux workspace. The full Python suite completed **931 tests:
931 passed, zero failed, zero skipped** (64.977 seconds). The isolated rootfs probes passed 8/8.
The focused discovery, normalization and CLI tests passed 27/27. The Node
console suite passed 8/8. The owned Docker fixture harness rejected all six
known-defective baselines and replayed all six preauthored development
references successfully. It made zero model calls and generated zero model
patches. These are owned-fixture/control results, not a repair-accuracy score
or certification for arbitrary third-party code. The historical registry
read-only audit passed (six repositories, 30 recorded tasks, no baseline
execution, no inference, execution not admitted). Sanitized counts and the
Docker evidence digest are recorded in
[local acceptance evidence](../evidence/phase26/local_acceptance.json).

The PR-triggered model-free Linux acceptance is pending publication. Its
workflow explicitly exercises owned Docker fixtures but does not install
customer dependencies or invoke any model. The next credible step is not a
bounty claim: an owner must
first choose a source that has a current, specific AI-agent allowance and a
narrow Python task, confirm U.S. payout eligibility and account route, and
authorize a new bounded DeepSeek budget only after all technical/security
gates are satisfied.
