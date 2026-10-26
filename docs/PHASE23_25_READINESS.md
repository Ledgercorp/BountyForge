# BountyForge Phase 23–25 readiness report

Date: 2026-10-26
Starting point: `ed983408b49713c4079b38e2b1763fad7c1ce24b`
Branch: `engineering/phase23-25-readiness-20261026`
Commercial admission: **NOT_ADMITTED**

## Outcome

This phase prepared a frozen historical task registry, improved strict agent
context and retry controls, added read-only crypto opportunity and Solana
receipt adapters, and rehearsed queue recovery and review state in private
SQLite. It did not run a model, submit work, create an account or wallet, or
receive funds. Fresh repair accuracy remains unmeasured. Real revenue remains
$0.

The registry contains 30 public historical SWE-bench Verified task metadata
records across six repositories. It contains issue digests, frozen base commit
identities, test IDs and primary license observations. It contains no issue
statement, patch, test patch, hint, solution or third-party source code. The
public dataset card has no explicit license; the harness itself is MIT, which
does not grant rights to the dataset or upstream repositories. For the
selected task revisions, GitHub reported a permissive recognized SPDX license
or a BSD primary notice, but full file, dependency and test rights are not
admitted. The data service did not prove that every row came from the pinned
viewer revision. Public training contamination is unknown, and the
engineering session can access the registry. This is model-free preparation,
not a held-out benchmark and not an authorization to fetch or run the projects.

The contract binds the registry digest, preparation code, metadata projection,
test identities, and a no-inference budget of zero. Its verifier rejects changed
task identities and attempts to relabel the set as unseen. The task agent
projection accepts only a short issue description, one hash-bound `subject.py`
source file, and approved editable line numbers. It rejects test/reference
fields. Timeouts and uncertain provider usage stop retries; at most one
correction is allowed after a known source or test failure. No actual requests
were made, so this phase measures no model accuracy, latency, token usage, or
API cost.

## Crypto discovery and qualification

The adapter uses official, fixed-origin GET operations for documented
Superteam listing/detail routes and Coinbase Exchange tickers. It does not
invent an OnlyDust listings API; OnlyDust data is accepted only as an explicit
unverified import. A Superteam feed request returned HTTP 401, which is
recorded as an authentication block with an unknown opportunity set. No
registration or API credential was created. A small public GitHub search
sample produced ten results, but no verified priced primary offer. One repeated
“earn 1 USDC” mention was an agent goal, not a bounty; the adapter now leaves
the advertised offer amount empty. The incomplete sample is not evidence that
the wider market has no opportunities. Captured GitHub search results lacked
issue state, so a regression caught and removed an incorrect “closed”
classification; the corrected evidence preserves availability as unknown.

The live read-only market observations in
`evidence/phase23-25/live-public-discovery.json` found SOL at $101.17 with a
venue-reported 24-hour volume of 246,041.5576272 SOL at the recorded timestamp.
The same venue returned HTTP 404 for USDC-USD; no peg value was inferred. A
ticker is not a guaranteed executable price, a withdrawal route or spendable
income. Only the canonical Solana USDC mint and native Solana SOL are recognized
by the Solana receipt parser. Other advertised assets remain unverified.

Qualification reuses BountyForge's existing gate and keeps funding, AI
permission, US eligibility, source rights, no-deposit participation and owner
payout-route evidence as separate facts. No expected return is computed while
success, acceptance, fees, engineering time, funding or collection probability
are unknown. Ads are not described as escrow. Human-only or advance-payment
signals are blocked. The reviewed OnlyDust Impossible Bench material requires
primarily human-authored core code and is excluded from agent work; this is a
program-specific decision, not a blanket statement about every OnlyDust
project. Immunefi's reviewed security program is research-only because it
requires expertise and execution outside the admitted Python profile.

## Dry-run workflow and payment evidence

The new CLI has an explicit read-only discovery mode and an explicit owned
simulation mode. It has no register, claim, submit, withdraw, or customer-code
execution operation. The simulation exercises a fictional opportunity through
an existing lease-fenced queue, a private SQLite ledger, expiry recovery,
duplicate suppression, a hash-bound review package, and a restarted process.
Even a valid test-only application HMAC approval cannot dispatch a submission.
Simulated 1 USDC is stored separately from received assets; actual earnings
stay $0. The real Solana client exposes only allowlisted read methods and was
used for a health probe only. No wallet or transaction was queried. Receipt
parsing explicitly does not attest wallet control, signature provenance,
spendable USD, legal withdrawal routes or economic fees.

The Phase 22 $2 DeepSeek authorization is closed and was not reused. No DeepSeek
credential was retrieved, no API call was sent and no credits were consumed in
this phase. Additional paid inference needs a new explicit budget authorization.

## Security and regression evidence

The local Codex Linux environment supported the existing unshare/rootfs
preflight. All eight owned namespace/rootfs tests passed with zero skips. The
opt-in owned Phase 8 Docker catalog also revealed a real test-harness defect:
private `0700`/`0600` temporary-copy permissions prevented UID 65534 from
reading the otherwise hash-validated fixture. After reproducing the failure, a
test verifies that only the disposable verified copy becomes `0755`/`0644`;
checkout permissions stay unchanged and the guest root remains read-only. The
final full local Linux suite with both opt-ins passed **924 tests, zero skipped**
in 63.551 seconds (63.913 seconds wall). Its child test-process CPU was 26.213
seconds and maximum reported child RSS was 42,132 KiB. The separate Node console
suite passed 8/8. The preserved owned Docker boundary and deliberate failure
controls are in `legacy-owned-docker-controls.json`; that record labels its
reference replay `DEV_ONLY_REFERENCE_VALIDATION`, with zero model calls and
zero model-generated repairs. The eight namespace tests have a separate
zero-skip receipt. Complete local evidence is in
`evidence/phase23-25/acceptance.json`.

The regression delta from Phase22's 881-test report includes Phase23
projection/retry controls, the 30-row metadata integrity check, crypto adapters,
receipt and queue state gates, process-boundary tests, the owned-copy mode
regression, and missing-state/decimal-boundary regressions. Those tests make no
model requests; the Phase22 inference budget remains closed.

Those namespace checks use owned probes only. They do not certify arbitrary
hostile repositories, customer code, package install scripts or private
execution. GitHub-hosted Ubuntu may still lack the facilities for the eight
namespace probes; CI must preserve those skips rather than disabling the
runner's security policy. The opt-in owned Docker regression runs against the
existing pinned Python image; it does not change the image or admit customer
execution.

## Work still blocked

* No historical source, dependency, or test-suite rights admission; no
  independently enforced hostile-code environment; no independent sealed
  evaluator. Therefore the 30 tasks cannot yet be executed or represented as
  unseen.
* No fresh paid-inference authorization. Phase 22's previously reported
  balance and six repairs are historical evidence only; they are not new Phase
  23 measurements.
* Superteam API access requires an owner-authorized account/key; no public
  listings were returned. OnlyDust has no established documented API in this
  review. The small GitHub search result is not a verified opportunity.
* No specific funded task with explicit AI permission, verified U.S.
  eligibility, accepted terms, a suitable source license and a validated
  execution boundary has passed qualification.
* No wallet, owner wallet binding, payout route, account/KYC, confirmed
  transaction, paid service or delivery workflow is active.
* Public market quotes do not establish a legally available, costed withdrawal
  path. Expected profit remains unknown.

The worktree and commits should be reviewed in draft PR #11. PRs #1–#10 and
`main` remain untouched. No production deployment, schedule, third-party
submission, customer contact, new spending or financial transaction occurred.

The next gates are independent source/test rights review and hostile-code
admission for any historical run, a truly inaccessible verifier before any
unseen-accuracy claim, a separately authorized inference budget, and owner-led
eligibility/payout setup for a specific primary-source crypto assignment.
