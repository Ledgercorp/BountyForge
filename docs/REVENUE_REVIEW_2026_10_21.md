# Revenue branch engineering review, 2026-10-21

Reviewed baseline `1f2833581ca6f9d96a0406c7c0a40dc9320cb3ba`, PR #2 targeting
`engineering/bounded-autonomy-20261020`. Both engineering branches were fetched;
main remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`, the base engineering
branch remains `e242e611983fee17f1709a465d23353677f7f634`. No merge or rewrite.
Earlier local Phase 5 evidence/verifier work is preserved in a separate worktree.
The v7 prompt experiment was stopped when this newer direction arrived.

## Baseline verification

Local cloud: 246 unittest cases, **239 passed / 7 skipped**, ten historical
harness tests and four dashboard tests passed. This reproduces hosted baseline
[39635335310](https://github.com/Ledgercorp/BountyForge/actions/runs/39635335310),
job 119344157270. Seven namespace/rootfs checks remain unexecuted.
No new Qwen run or live model request was made in this review.

## Verified defects and corrections

Payment gate accepted full-privilege `sk_live_` keys despite requiring a restricted
read-only credential in its operating contract. It now admits only bounded live
restricted-key syntax; actual assigned Stripe permissions still require separate
verification. Charge evidence must independently confirm `amount_captured`
matches the exact approved price, in addition to the existing Checkout and
PaymentIntent checks. Missing, boolean, partial and excessive capture values
fail closed. No Stripe API calls or financial writes were made.

The paid-review ledger accepted a boolean schema version and an existing state
without a CAS revision. It also mutated a store's returned object before a failed
CAS if that store returned a shared reference. It now rejects corrupt/unversioned
state and copies validated state before editing. Payment verification still
precedes deduplication, and no result authorizes execution or delivery.

Red proof: eleven Stripe test methods produced five subtest failures; nine ledger
test methods produced three failures. After fixes: **11/11 Stripe and 9/9 ledger
tests passed**, `git diff --check` passed. All provider evidence in these tests is
mocked, with synthetic identifiers; no live payment or revenue was observed.

Other verified review findings are being integrated: incomplete GitHub search
and exhausted metadata budgets must not masquerade as successful zero-result
observations; model workflows need shared single-worker concurrency, secret scope
reduction and a canary gate that rejects blocked/incomplete task sets.

## Authorization and deployment

Repository secret-name inspection returned HTTP 403 (integration lacks that
permission). This does not establish whether a key exists. The current Groq
account plan is not independently available through this session. A repository
variable is at most an attestation, not billing proof; no real model request is
authorized by its mere presence. Never paste credentials into chat or evidence.

No deployment, public sales, merge, new recurring work, external submission,
customer communication, contract or financial action. Purchases and paid API
usage $0; confirmed revenue remains $0. Existing dashboard and synthetic ledger
are untouched. Real Groq comparison and private customer execution remain blocked
on their separate account/security authorizations.

## Consolidation and remaining technical gates

`8892f75` contains the payment/CAS fixes. `9e46c80` introduces a private-volume
SQLite review-store adapter with actual concurrency and crash-recovery tests.
Independent review then added continuous permission checks, cleanup-error safety
and rejection of databases inside the source checkout. No private production
volume is connected; temporary test files do not establish durable deployment.
See [private store contract](PRIVATE_PAID_REVIEW_STORE.md).

The scout now distinguishes incomplete observations from completed bounded zero
samples. Its schedule was removed, and push/PR regression uses offline data;
manual read-only research remains available. Existing live zero-credible-lead
findings are preserved; no new live scan was required by this review.

All model workflows share the existing single-worker concurrency group. The Groq
key is supplied only to the model step after independent Docker preflight.
The canary uses the unchanged structural v5 fixtures by default, at most eight
requests, one per minute, and an explicit opt-in 1,024-token total reasoning cap.
The patch interface remains at 150 tokens, the final response at 3,000 bytes,
and source/syntax/capability validators remain mandatory. The default adapter
retains its prior total allowance. Low reasoning effort avoids an undocumented
medium default; returned reasoning is not retained. Provider failure disables
the instance; credential echoes are rejected and metadata is cleared before
failed requests. This is staged configuration, not a real-model measurement.

The canary gate independently checks complete task/call/token/source provenance
and rejects unavailable/blocked execution. A further step without the key
reconstructs successful responses, checks their exact diffs, proves fresh Docker
admission and reruns owned tests with zero inference. Its positive unit fixture
uses a neutral comment with mocked Docker and is **not** a model repair success.

The [provider review](FREE_MODEL_ADMISSION_REVIEW_2026_10_21.md) checks current
official Groq, Gemini and OpenRouter policies without inference. No account was
admitted and no model-quality ranking is established. Groq is the next prepared
comparison because its adapter exists; it is not a proven best-performing free
model. Public free-tier advertising does not attest the owner's account.

Two secret/variable metadata requests returned HTTP 403. No permission was
bypassed, key read, plan attestation set or live canary dispatched. The next
account action requires secure owner verification of current Free Plan, quota,
provider terms and the scoped credential. The private paid path separately needs
an approved durable volume, narrow source/test contract, private execution
admission, proven coding results and owner-approved offer/delivery terms. Payment
alone never grants code execution, publication, customer contact or delivery.
