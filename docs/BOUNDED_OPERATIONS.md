# Bounded internal operations

The operational workflow is `.github/workflows/bounded-operations.yml`. On the
engineering branch it accepts explicit dispatches and tagged workflow changes.
It does not activate recurring production repairs or submit upstream work.

## Execution and publication planes

1. A read-only job runs regression, sixteen scripted fault scenarios and live
   discovery. Discovery outputs canonical issue URLs and unverified statuses.
2. A trusted coordinator validates that envelope and writes only
   `state/ledger.json` on `state/bountyforge-ledger-v1` in this repository.
   GitHub Contents SHA preconditions reject concurrent writes. The data branch
   is initialized from the engineering branch; it is not a deployment branch.
3. The existing SQLite Queue operates transiently on that bounded JSON snapshot.
   A claim is durable before any model starts. One active global lease, fencing
   tokens, at most two interrupted claims and 15-minute expiry prevent stale
   completions and permit recovery. A revision/date pair is idempotent.
4. A separate read-only job starts the pinned local Qwen server with one stream
   and runs the existing `auto_line` worker over the owned addition fixture.
   Original and generated code execute only in admitted, offline Docker.
   Container controls are probed before execution. No write-capable token enters
   this job's environment, model request or container. Checkout credentials are
   removed. No Docker socket or host credentials are mounted in the guest.
5. A fresh trusted publisher validates the evidence envelope, exact revision and
   live lease. It records the digest and Actions run URL, marking success as
   `synthetic_review_ready`, with `commercial_review_ready: false`.

The lease token is a fencing identifier, not a GitHub authentication credential.
It cannot publish without the independently scoped repository token. Only
trusted same-repository branch events can start these jobs. No fork artifacts,
issue-provided commands, model paths or repository target code run in the
write-capable coordinator. Contents write permission is necessarily repository
scoped; trusted code fixes the only allowed ref/path. Branch protection can
further constrain this independently. There is no publication-to-upstream code.

## Durability, budgets and failure handling

The remote GitHub file is authoritative. A runner's SQLite file is never the
sole permanent state. Failed CAS writes authorize no claim or execution.
Interrupted workflows leave durable leases; a subsequent run reclaims an
expired lease, and a second interruption becomes terminal `lease_exhausted`.
Old source revisions are closed as failed before selecting a current job.
Only one synthetic opportunity per source revision per UTC date runs; repeats
on the same date demonstrate duplicate suppression rather than repeated repair.

The ledger has a 512 KB limit, 100 repair jobs and 1,000 unverified discoveries.
It fails closed when full. This is bounded coordination, not indefinite free
storage. Archive/retention design must be reviewed before reaching capacity.
Artifacts are small JSON files retained one or two days. The nonsecret pinned
model cache is restored without a new cache-write step. Standard public Ubuntu
runners only; no larger runners, paid APIs or other services are provisioned.
Repository visibility changes or different runner classes invalidate this scope.

The owned fixture admission compares exact catalog files/tests and replays its
single body-line modification through `stage_lines`. Curated historical task
admission separately binds all tests and validates proposed source changes.
Neither route admits arbitrary current third-party repositories. Independent
hostile-code security certification remains absent. Seven namespace tests remain
skipped unless their separately built rootfs is supplied.

## Qualification and owner review

All scanned opportunities remain `unverified_candidate`, non-executable and
funding-unverified. Tier B advertisements can be researched but are not actionable
without independent escrow or binding-funding verification. Current adapters do
not provide that attestation. AI authorization, location eligibility, open and
available reward status, payer identity, payout/acceptance terms, no fee and
execution safety must also be supported independently. Candidate booleans do not
create authority. No qualified real opportunity or revenue is claimed.

Real opportunity repairs require an admitted execution boundary and independent
commercial evidence. Synthetic and historical successes cannot become commercial
review-ready candidates. Specific upstream submissions always require owner
approval through a structurally separate action. No acceptance of contractual or
financial terms is part of this workflow.

## Schedule activation gate

Proposed conservative cadence: `17 6 * * 1,3,5` (UTC). Do not add an active cron
until hosted complete cycles, duplicate suppression, negative isolation and
recovery evidence have passed review. GitHub schedules run from the default
branch. Adding cron to this feature branch would not prove unattended operation.
Keep main as the production baseline and PR #1 draft while launch gates remain.
The existing Hatchable read-only discovery deployment is independent; this work
does not replace its source or credentials. The durable ledger and Actions links
provide a read-only owner review source without injecting write tokens into the
public dashboard.
