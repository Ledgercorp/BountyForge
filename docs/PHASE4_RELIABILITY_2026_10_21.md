# Phase 4 reliability and private readiness

Internal readiness: **DRY_RUN_READY**. Paid customer operation: **NOT_READY**.
Confirmed revenue $0. Main, both draft PRs, dashboard v11 and synthetic ledger
remain separate. Starting feature HEAD was `3909c1e50c2e7891afb4ebd50f93555d62fd9733`.

## Implemented and frozen repair architecture

Core freeze `5f3f0cc668d3993f013759133223e204fa61c904` precedes unsealing the
independently authored evaluation cases. The original line protocol remains
available. Opt-in `ast_statement_v1` derives complete statement spans or
If/While condition-expression spans from trusted approved anchors. It supports
multiple related edits with original-offset application, retains indentation,
rejects ambiguous inline layouts, preserves definite direct assignment names,
and reuses the exact capability/declaration checks. Trusted compilation adds
context-validity checks without executing target code.

The existing worker now records bounded statement-call transcripts, exact
validator/test feedback, semantic candidate hashes and fresh-copy verification.
Repeated AST-equivalent failed candidates avoid another test execution; invalid
proposals remain non-executable. The earlier validated-sibling retry fix stays
intact. No expanded file paths, new callable/attribute capability, provider
fallback or weaker sandbox was introduced. Binding preservation is conservative,
not a proof of complete source behavior; regression tests remain essential.

TDD and independent review caught module-level return acceptance, indentation
normalization and definite-binding gaps before evaluation. Twelve neutral
statement/worker methods passed; full core-freeze regression was 333 total,
326 passed and seven existing rootfs skips. No historical repair was rerun.

## Security acceptance actually executed

Integrated security commit `e551ff5` reproduces an owned chmod attack on the
prototype rootfs, then fixes it using a read-only bind mount inside the disposable
namespace. It also rejects source/launcher symlinks before canonicalization and
requires integer timeouts. See `PHASE4_NAMESPACE_SECURITY_2026_10_21.md` and
`evidence/phase4-security/` for commands, environment and original/red/green logs.

On this existing Codex Cloud Linux environment, the unchanged namespace preflight
succeeded and **all original seven checks plus the new immutability check ran
and passed**. No root/privileged container, host policy change, Mac, download or
new infrastructure was used. GitHub Ubuntu's separate UID-map restriction is
not bypassed. Its default suite now explicitly skips eight rootfs tests, including
the newly added test; this is not a claim of hosted namespace acceptance.

Integrated local regression with the real rootfs: **350/350 passed, zero skipped**.
Hosted [39696038176](https://github.com/Ledgercorp/BountyForge/actions/runs/39696038176)
at `71c2d4d62d876dfad3430d22ce9cfd1cb6d10a27`: **350 total, 342 passed, 8 skipped**.
Historical harness 10/10 and dashboard 4/4 passed locally. Arbitrary private code,
rootfs provenance admission, dedicated cgroup controls and dependencies remain
unadmitted; production still uses the existing curated/owned Docker boundary.

## Private commercial integration

`36bbb02` adds a separate metadata-only private scope journal. Owner-key HMAC
scope records bind prior verified-payment review hashes, source/test identities,
receipt references and expiry. Atomic CAS, one review lease, fencing/recovery,
and idempotent cancellation/refund/revocation/failure holds are implemented.
No source is accepted and no financial refund is issued by a hold. Ten focused
tests passed. Existing Stripe gate, paid-review schema and synthetic coordination
are preserved. HMAC proves secret possession, not independent identity/consent.

Execution and delivery remain structurally false. No signer/key, production
volume, customer order, public offer, source intake or delivery is configured.
Fresh payment evidence, independently admitted private execution/dependencies,
verified rights/model-sharing consent and specific owner delivery approval are
still required. See `PRIVATE_SCOPE_REVIEW.md`.

## Independent evaluation protocol, before inference

Catalog origin commit `7687104d0b34d43f6b08ce598df2e764e467ec3b` was independently
authored and frozen without giving the implementation agent task details until
the core freeze. Integrated catalog commit `71c2d4d` adds four original owned
maintenance cases with source/test SHA pins and provenance. No manual solutions,
upstream fixes, external repositories or customer code are included.

The planned controlled comparison gives the same GPT-OSS model one call per
case per protocol, eight calls total, 1,024 total generation tokens/call, 60-second
spacing and counterbalanced order. Baselines execute once per pinned case and
are re-admitted before cached reuse. Candidate code must exactly reconstruct
from recorded bounded output before Docker execution. A separate step without
the key independently replays successes. Raw usage, runtime, rejections and
interruption checkpoints are retained. `evaluation-freeze.json` records the
core/catalog identities and budget; no new live score exists at this checkpoint.

These are owned synthetic maintenance cases. Even a passing controlled comparison
cannot establish general model improvement, real-world accuracy or commercial
readiness. The original historical 1/5 and owned 2/4 GPT-OSS scores are preserved.

## Evaluator review and integration — 2026-10-22 UTC

`6730d57`, `3184d82` and `8e28309` implement the paired evaluator and
credential-free replay. Independent review required exact pinned-catalog binding,
durable pre-HTTP call intents, complete terminal states and call counts,
independently reproducible rejection records, and all-record validation before
any replay execution. Incomplete or interrupted experiments are blocked and
cannot become a completed accuracy score. Twenty-five catalog/evaluator/replay
tests pass, including a mocked positive replay and negative tampering, timeout,
credential, interruption and sandbox cases. Those mocks are not repair results.

Final pre-inference integrated regression at `8e28309`: **372/372 passed,
zero skips**, using the already prepared trusted rootfs in Codex Cloud Linux.
Historical harness **10/10** and dashboard **4/4** passed. The manual-only existing
canary gains a `maintenance_pair` selection; no schedule, new infrastructure or
public/customer execution is enabled. YAML parsing and all six shell blocks pass
syntax checks; actionlint is not installed. Hosted acceptance and live comparison
are pending at this checkpoint. No model calls have been made in this phase.
