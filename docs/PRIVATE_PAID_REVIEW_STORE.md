# Private paid-review store (not deployed)

`SQLitePaidReviewStore` implements the existing `PaidReviewLedger` CAS contract
with an actual SQLite transaction. It stores only validated review records, not
executable jobs, customer source, session IDs, contact information or credentials.
It remains separate from the public synthetic ledger and existing repair queue.

The caller must supply an explicit absolute path on an **approved private,
persistent volume**, owned by the trusted coordinator. Parent permissions must
be `0700` or stricter; the regular database file must be private (`0600`), owned
by that coordinator, have exactly one filesystem link and not be a symlink. Every connection rechecks those
conditions. SQLite uses full synchronization; `BEGIN IMMEDIATE` atomically checks
the expected revision and replaces the single bounded state row. Stale writes
fail rather than retrying blindly. Corruption does not become an empty ledger.
Payment state inside the source checkout is rejected before creating a database.

Tests use temporary cloud files and synthetic payment evidence. Actual tests cover
reopening the store, simultaneous coordinators for one payment, stale CAS,
permission changes, corruption, cleanup errors and killing a process during an
uncommitted transaction. No live Stripe order was created or read in these tests.

No production volume, endpoint, credential or service was configured. Ephemeral
Actions disks or Codex workspaces are **not** permanent paid-order coordination.
Do not upload this database into a public repository, cache or artifact. Private
backup, retention, volume recovery and operations approval remain deployment
gates. A future backend can implement the same atomic contract without changing
the review gate; no new paid server or permanent VM is required by this code.

Even a persisted, verified payment emits only `awaiting_owner_scope_review`.
Scope consent, exact source/test revisions, dependency admission, private code
execution, actual model acceptance and authorized delivery remain separate.
There is no path from this store to worker dispatch or customer communications.
Payment cannot authorize arbitrary source execution. The proposed $49 offer
remains unpublished, and confirmed revenue remains $0.
