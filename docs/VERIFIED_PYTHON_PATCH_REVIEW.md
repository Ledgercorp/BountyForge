# Verified Python Patch Review — inactive owned-only prototype

**Owned-only; not a live offer. Launch, intake and delivery are disabled.** This
slice prepares a reviewable local package for one exact repository-owned fixture.
There is no customer upload, customer source path, customer code execution, model call,
provider configuration, payment, refund, external delivery or deployment route.
It costs $0 to run locally and does not use secrets or contact anyone.

The eventual product direction is a **patch-only review**: a customer reviews a
diff and runs their own trusted tests in their own environment. The name
“Verified” must always specify what actually ran. Here it means only the exact
Phase7 owned minimal reproduction passed four deterministic local vectors.
`customer_environment_tested` and `customer_tests_run` remain false. This package
is not evidence of an AI repair: the included arithmetic patch was manually
authored in Phase7, and `model_calls` is zero.

## Scope proposed for owner review

A future supported request would be one small Python file and one function,
standard library only, with a deterministic minimal reproduction, stated
expected behavior, explicit review/modification rights and no secrets or
sensitive data. This does not enable such requests today. The only runnable
fixture now is the exact owned `total(a, b)` subtraction-to-addition repair.

Unsupported work includes multi-file or dependency changes, network or secret
access, nondeterministic failures, production access/deployment, arbitrary
customer code or selected commands, security certification and correctness
guarantees. A customer's authorization does not enable this prototype to execute
customer code. Do not add customer material to the fixture or its replay.

Before future intake, the owner must separately approve an intake policy and
obtain explicit rights to review/modify the material. Any proposed sharing with
a model provider needs separate explicit permission naming the provider,
material, purpose, scope and retention terms. Ownership permission alone is not
model-sharing permission. No such consent is accepted or represented as verified
by this owned-only prototype.

## Privacy, retention, deletion and failure proposals

No customer data is collected, stored, logged or shared by this interface.
Rejected stdin/argument contents are not echoed. Owned packages persist in the
operator's explicitly selected private directory until that operator removes
them. There is no remote copy, automatic expiry, retention scheduler, secure
erasure guarantee or deletion of existing packages. Local hashes detect changes
to these fixed owned bytes; they are not signatures, rights evidence, delivery
authority or unforgeable proof of past execution.

**The following are proposals for owner review, not a contract or live offer:**

- Minimize future intake; prohibit secrets and unnecessary personal data.
- Delete submitted source and derived packages within seven days of completion
  or rejection, or earlier on a verified deletion request. Before intake, specify
  backup and provider retention/deletion limits and implement the agreed policy.
- Reject unsupported scope before acceptance. Disclose any failed verification
  and offer no verified claim when a reproduction cannot be confirmed.
- Refund unfulfilled accepted work in full under owner-reviewed terms finalized
  before any sale. No charge, refund, money movement or financial commitment
  occurs in this prototype; legal and commercial terms remain unapproved.

## Local owned package

From the repository root, create a private local directory and run the fixed
mode. These are operator commands for this owned fixture only:

```sh
mkdir -m 700 /tmp/bf-owned-review
python -m scripts.patch_review_service --owned-only-package --output-dir /tmp/bf-owned-review </dev/null
```

The output directory must already exist, be absolute, belong to the operator and
have no group/other permissions or symlink components. It may contain other
owner files, which are untouched. A fresh fixed subdirectory
`owned-review-package` is created with mode 0700; its files are 0600. Existing
packages are never replaced. Failed writes attempt to remove only the new files
and subdirectory this invocation created.

The package contains:

- `owned_before.py` and `owned_after.py`: exact owned source and manual repair.
- `repair.patch`: the actual unified diff for `owned_total.py`.
- `review.json`: bounded canonical JSON with before/after/diff and file SHA-256,
  honest replay evidence, limitations, proposed policies and disabled controls.
- `REVIEW.txt`: static customer-run review instructions for the future workflow;
  it selects no customer commands and executes nothing.

The stdout receipt hashes the exact canonical review manifest, identifies the
owned-only disabled state and records total file count and bytes. The verifier
`bountyforge.patch_review_service.verify_owned_package(path)` checks the fixed
file set, private regular files, single links, bounded reads and exact known
owned contents. Corruption, extra files, public files, symlinks and hardlinks are
rejected. Each file is capped at 32 KiB and the entire fixed package at 64 KiB.
It accepts no proof that upgrades launch, delivery, rights or verification.

The CLI rejects unknown, abbreviated, duplicate or oversized arguments, customer
source/path flags, deceptive execution/delivery/verification flags, all nonempty
stdin and oversized stdin **before writing**. Stdin reads at most 4097 bytes and
rejects every supplied byte; an open pipe must close or provide input for the
read to complete. Only the explicit owned-only mode and private output directory
are accepted. Help and every successful/error response identify the owned-only,
non-live state. No expiry/revocation workflow exists because this package grants
no permission; commercial ledger authority remains outside this slice.

For a future customer-run workflow, the customer would compare the original
SHA-256, inspect every diff, apply it in a controlled checkout, choose their own
existing trusted test workflow, assess the results and decide whether to keep or
revert it. This prototype neither supplies model-selected customer commands nor
runs any customer environment. Local integrity checks do not establish customer
correctness, AI effectiveness, commercial readiness or external delivery.

## Verification

```sh
python -m unittest discover -s tests -p test_patch_review_service.py -v
```

The focused tests include actual subprocess refusal checks with no writes,
unified-diff reconstruction, replay evidence and honest verification flags,
canonical package integrity, file permissions, corruption and forged manifest
claims, symlink/hardlink/extra/oversized/FIFO rejection, duplicate prevention and
write-failure cleanup. Frozen benchmarks and existing launch controls are
unchanged.
