# Private paid scope review journal

Status: implemented and offline-tested; **not deployed and not an execution
authorization system**. No source, customer order, owner approval credential or
private persistent volume is configured. Confirmed received revenue is $0.

`bountyforge/paid_scope_review.py` adds a metadata-only bridge from an existing
private payment-review record to scope review and safe interruption recovery.
It does not alter `PaidReviewLedger`, its schema/table, the existing payment
database, the public synthetic ledger, Stripe configuration or any worker.
The new database refuses an existing payment-review database or other schema.

The trusted coordinator must supply an owner-controlled 32–64-byte HMAC key.
The module verifies approvals; no production signer, intake endpoint, deployment
or secret setup is supplied. Approval payloads bind an exact payment-session
hash, one Python source path and source/test hashes, the fixed unittest test
path, stdlib-only dependency policy, owner approval identifier, expiry, and
source-access/model-sharing receipt hashes. Unexpected fields, customer
`owner_approved` booleans, altered signatures, unknown payment reviews, expired
approvals and changed scope on the same payment fail closed.

HMAC proves possession of the configured shared secret, **not** independently
verified owner identity, contractual consent or customer rights. Receipt hashes
are references, not proof that their documents have been verified. Metadata
source hashes are not matched to customer files because no customer files are
accepted or read. The trusted coordinator, key provisioning and source/consent
evidence still need separate owner authorization and review.

Successful recording yields `awaiting_private_execution_admission`, with
`execution_authorized=false`, `delivery_authorized=false`,
`source_accepted=false` and `payment_freshly_verified=false`. An existing
payment review is historical evidence only. Future fulfillment must retrieve
fresh provider evidence independently; neither a payment snapshot nor the
HMAC approval can switch execution on.

The separate private SQLite state uses existing connection/privacy checks:
absolute path outside the checkout, private directory/database ownership and
permissions, no linked database, synchronous transactions and atomic CAS.
The journal has at most 100 plans, 32 events per plan and 256 KiB of serialized
state. It does not create or configure durable hosting. Ephemeral unit-test
files are not evidence of production persistence or backup readiness.

Review-only leases allow one active coordinator across all plans. A lease is
bounded to 300 seconds and approval expiry; only its token hash is stored.
Recovery increments a monotonically increasing fence and rejects old tokens.
Do not send lease tokens, approval material or payment metadata to a model or
public artifact. Clock values are trusted coordinator inputs, not customer
request fields. Failed CAS is terminal; there is no blind retry.

Cancellation, refund/dispute observation, owner revocation and repair failure
are idempotent blocking events. They invalidate any review lease, increment
its fence, preserve all accumulated hold reasons and cannot be undone through
this interface. Event capacity reserves slots for all four blocking events.
A refund hold records an observation; it does not issue a financial refund.
Storage failure remains a terminal error and authorizes no execution.

`delivery_review()` always returns a blocked result explaining the missing
private execution, exact source matching, fresh payment, independent repair
verification and specific owner-delivery approval. There is deliberately no
transition to executable, customer-review-ready or delivered states, and no
method for accepting source archives or invoking a test runner/model.

Verification on the standalone worktree based on `3909c1e`:

- Initial seven feature tests failed because the journal was absent.
- Ten focused tests passed: signature/scope binding, existing-payment binding,
  idempotent persistence/restart, stale CAS/privacy rejection, expired lease
  recovery, cached approval-key mismatch, global concurrent-claim exclusion,
  all four safety holds, event exhaustion, corruption and delivery denial.
- Full local regression: **331 total, 324 passed, seven existing rootfs skips**.
  No skipped rootfs check was run by this slice.
- No live model, Stripe request, customer source execution, deployment,
  public offer, external submission, purchase or financial operation occurred.

Remaining blockers: independently admitted private execution/dependencies and
recovery; approved persistent deployment/backups; verified source/customer
rights and model-sharing terms; fresh payment; broader repair quality; owner
approval of offer/contract/delivery. This journal prepares review evidence only.
