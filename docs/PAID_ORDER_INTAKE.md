# BountyForge paid-order intake and proposed $49 Python Fix Sprint

Status: **engineering draft; not for sale and no customers enrolled.**
Last independently verified 2026-10-21. This is not a financial commitment.

## Live account evidence

Read-only Stripe connector access returned an existing **BountyForge** live
account. At inspection time:
- Checkout Sessions: empty.
- PaymentIntents: empty.
- Payment Links: empty.
No current paid order, revenue or published BountyForge Stripe checkout could
be substantiated from this account. Do not create or share a commercial link
without an explicit owner decision on the deliverable, terms and service.

## Proposed offer for first controlled pilot

**Python Fix Sprint · $49 one-time fixed price.**
Scope and acceptance terms for owner approval:
- One specific reproducible Python defect in one existing module, a concise
  error report and an objective regression test supplied or agreed in advance.
- Python-only small projects that fit the existing isolated pinned-fixture
  worker's code/test policy. No arbitrary downloaded dependency installation.
- Output: proposed patch/diff, passing evidence, short explanation and one
  bounded revision for the stated defect.
- Exclusions: arbitrary executable archives, production credentials, remote
  shell, exploit development, large multi-file features, emergency response,
  guaranteed defect resolution and any project we cannot safely sandbox.
- Files and exact source/test permissions are accepted **before** charge.
  If security admission or requirements fail, decline the job; do not take
  money for a service that cannot be delivered.
- Manual owner approval remains mandatory for outside publication and for
  terms, refunds or disputes. The model does not send customer correspondence.
- No guaranteed completion time, outcome or profitability is asserted here.
- Payment processing fees, refund rights, taxes and applicable platform terms
  must be reviewed before a public sales launch. Fees reduce net earnings.

## Payment-provider proof, implemented read-only

Code: `bountyforge/stripe_order_gate.py`
Tests: `tests/test_stripe_order_gate.py`
Hosted CI: https://github.com/Ledgercorp/BountyForge/actions/runs/39633092243

The gate fails closed until **all** of these exist in its **trusted**
environment:

- `STRIPE_SECRET_KEY`: a live restricted Stripe API key with **read-only**
  Checkout Sessions, PaymentIntents and Charges permissions. Never give it
  to the model, code sandbox or untrusted source, commit it or print it.
- `BOUNTYFORGE_APPROVED_PAYMENT_LINK`: exact, independently approved
  `plink_...` ID from the BountyForge Stripe account.
- `BOUNTYFORGE_APPROVED_AMOUNT_CENTS`: exact approved price in USD cents,
  proposed `4900` only after owner approval.
- Payment Link metadata to configure:
  `bountyforge_service=python_bugfix_basic` and `contract_version=1`.

Official Stripe docs confirm Payment Link-level metadata is copied into
Checkout Sessions. The provider controls this metadata, not issue text.

The gate independently retrieves the exact Checkout Session, matching
PaymentIntent and matching Charge over fixed-origin GET-only HTTPS. It requires:
- Live-mode, completed, paid, one-time USD Checkout Session.
- Exact amount, Payment Link ID and service/version metadata.
- A `succeeded` PaymentIntent for the exact amount.
- A `succeeded`, captured, paid Charge with no refund or dispute at
  verification time.
- No redirects, proxies, payment writes, model calls or delivery actions.

Evidence includes only the SHA-256 of the session ID and non-sensitive
service/amount details. It **never** returns credentials, customer email or
card details. The output explicitly contains `execution_authorized=false`
and `outside_submission_authorized=false` even for a verified payment.

**Known limitation:** the Charge can be refunded/disputed after the moment
of verification, so fresh Stripe evidence is required again before any
fulfillment step. Payment authorization is not evidence of actual bank payout.

## Why we do NOT switch on checkout now

BountyForge's last historical held-out real-model benchmark was 0/5 verified
repairs; synthetic owned fixtures alone are not sufficient for customer work.
The stronger Groq model completed **2/4 owned structural repairs**, both
independently replayed in run `39677572877`. That development result does not
establish paid-job reliability, and the existing sandbox does not admit arbitrary customer
repositories. It would be irresponsible to promise an autonomous $49 fix until
the claim is measured on reproducible held-out tasks, privacy is reviewed and
the owner approves public service terms.

## Next concrete engineering gates

1. Verify BountyForge's current Stripe live account readiness and obtain
   explicit authorization for the offer's scope and fixed pricing.
2. Preserve the completed owned GPT-OSS benchmark; verify broader fixed
   evaluation evidence, inference privacy and applicable quotas before a pilot.
3. Develop a private intake workspace with a fixed source contract, threat
   model and customer-specific tests; do not put private customer code in a
   public GitHub Actions run or artifact.
4. Admit **only** owner-approved customer source to an independently reviewed
   isolation and test execution environment.
5. Define lifecycle: lead -> scoped -> payment verified -> admitted ->
   isolated fix -> test/evidence -> owner-reviewed delivery -> delivered.
   Every transition needs proof and durable idempotency.
6. When admitted, enable a monitored worker with quota and stop conditions.
   No secret, payment, card, PII or business correspondence passes to models.

Initial payment-gate milestone: **30/30 new-work hosted Linux tests passed** (13 discovery,
8 hosted inference mocks, 9 payment-evidence mocks), but zero commercial
sales, zero verified bounties and no production activation.

For current integration fixes, private review-store tests and deployment blockers,
see [revenue review](REVENUE_REVIEW_2026_10_21.md) and
[private store contract](PRIVATE_PAID_REVIEW_STORE.md). The store is review-only,
separate from the synthetic ledger, and rejects state inside this source checkout.

The offline-tested [private review command](PRIVATE_PAID_REVIEW_COMMAND.md) now
connects that store to fresh read-only provider checks. It accepts no source,
dispatches no repair, and has no deployed private volume or public endpoint.
