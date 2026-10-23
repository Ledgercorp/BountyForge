# Private paid-order review command

Implemented, offline-tested, **not deployed**. No approved persistent volume,
public sales offer, customer order, source intake or fulfillment worker exists.
This is a trusted-coordinator integration of existing components, not a new
commercial execution system.

`python -m bountyforge.paid_intake --store /approved/private/review.sqlite3`
reads one bounded live Checkout identifier from standard input. Do not put an
identifier or credential in command-line arguments or public logs. Only a
trusted owner-operated coordinator may invoke it, after service/price/Payment
Link approval. It is not an HTTP endpoint and is not added to Actions.

Required deployment facts:

- An explicitly approved persistent private volume outside the checkout, with
  directory mode 0700, database 0600, correct owner and no linked database.
- `BOUNTYFORGE_PRIVATE_REVIEW_STORE_APPROVED=1` records the operator assertion;
  it cannot independently prove volume persistence or adequate isolation.
- Existing restricted read-only Stripe configuration from `PAID_ORDER_INTAKE.md`.
  Key syntax does not attest actual Stripe permission scopes.
- No model or publication credentials in the coordinator environment. The
  command rejects known Groq/OpenAI/GitHub credential variables and refuses
  GitHub Actions. This is an extra guard, not a general secret detector or
  proof that an arbitrary environment is safe.

The command rejects invalid/oversized/source-like input before network or
storage, validates the private store before provider requests, retrieves the
Checkout Session, PaymentIntent and Charge fresh on every review, then records
at most one review using atomic CAS. Refund/dispute/unpaid evidence rejects,
including on replay. Store/privacy/provider failures have sanitized enumerated
results and a nonzero exit; there is no blind retry. CAS/crash and interruption
semantics are inherited from the separately tested private store.

The output contains only review status, a session hash when verified, and
explicit false execution/submission/source-acceptance/fulfillment flags. It
never calls a model, test runner, execution queue or delivery mechanism.
An old review remains historical evidence if a later check rejects; it does
not authorize work. Fresh payment checks remain required at any future
fulfillment boundary.

Seven integration tests use mocked fixed-origin GET responses and real ephemeral
private SQLite files: completed-order persistence/restart and duplicate fresh
reads, refund after review, unpaid rejection, bounded invalid/source input,
mixed credentials/unapproved environment, and privacy/provider failure.
An injected durable-write rejection also proves that no success is emitted
and no blind retry occurs after payment verification.
These are not live payments or production durability evidence.

Remaining fulfillment gates: separately approved persistent private deployment,
customer-specific source/test/scope and model-sharing consent, independently
admitted private execution, broader repair quality, approved commercial terms
and owner-reviewed delivery. No payment alone can satisfy those gates.
