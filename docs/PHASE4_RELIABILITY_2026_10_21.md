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

## Historical failure-to-mechanism trace

The exposed five-case analysis motivates generic machinery, not another tuned
historical score. Frozen expectations and original reports remain unchanged.

| Observed failure | Implemented generic response | Limit |
| --- | --- | --- |
| 454: indentation errors and false rejection of an already validated sibling | Deterministic indentation/statement spans; preserve the prior sibling retry correction | No historical rerun this phase |
| 459: invalid indentation and candidate losing a required binding | Whole-statement parsing, compile validation and conservative direct-binding preservation | Not a complete data-flow or semantic proof |
| 475: a physical-line edit left a multiline continuation invalid | Replace the AST statement or condition-expression span | Ambiguous layouts still rejected |
| 524: proposed replacement exceeded the physical-line budget | Multiple bounded disjoint statement proposals are available | Per-proposal limits remain; no guaranteed repair |
| Repeated ineffective owned proposals | AST-equivalent candidate fingerprints skip duplicate test execution; retain exact failure feedback | Requires inference to know a new proposal repeats an old one |

The original line protocol remains an explicit supported choice. There is no
implicit statement fallback, arbitrary path selection or increase to model-call
budgets. Pure syntax validation never executes target code. Passing tests still
cannot prove preservation of every behavior outside the tested contract.

Catalog files are reproducible from integrated commit `71c2d4d`; the separate
original authoring freeze was `7687104d`. Their exact source/test identities are
pinned by the manifest and evaluator. The fixed core remains `5f3f0cc` throughout
the comparison; evaluator admission changes did not modify that core or cases.

## Completed paired measurement — 2026-10-22 UTC

[Run 39697530398](https://github.com/Ledgercorp/BountyForge/actions/runs/39697530398)
at `e712bdf86b1475501153c68c1ce334411949fac4` completed successfully, including
all Docker admission controls and independent replay without inference,
payment or publication credentials. Four original baselines reproduced as
assertion failures. Exactly eight calls completed; no case was blocked.

| Frozen owned case | Existing line/v7 | Statement/v1 |
| --- | --- | --- |
| page_window | Passed + replayed | Passed + replayed |
| utc_offset | Syntax rejected | Passed + replayed |
| integer_fields | Replacement budget rejected | Replacement budget rejected |
| retry_delay | Passed + replayed | Passed + replayed |
| Total | **2/4, four calls** | **3/4, four calls** |

All five successful proposals passed fresh independent Docker regression. The
statement worker additionally performed its required fresh-copy check. The line
proposal for utc_offset replaced a multiline return's first physical line and
left its original continuation lines; whole-source parsing rejected it. The
integer_fields proposals contained eight and five physical lines respectively,
exceeding the unchanged three-line bound. Both were rejected before execution.
Their logic was not tested; they are source-validation failures, not observed
regression failures. No safety rule, fixture, test, prompt or core was changed
after seeing these results, and no second experiment was requested.

Usage: **8,815 prompt + 2,381 completion = 11,196 tokens**. Completion includes
**1,886 reasoning tokens**. Line usage: 4,098 prompt/1,454 completion; statement:
4,717 prompt/927 completion. Adapter wall time **418.889 seconds includes
request pacing**; model job duration **450 seconds**. Pure inference latency
was not separately measured. The 60-second spacing makes per-arm wall times
unsuitable as direct inference-speed comparisons. Eight calls is the same
fixed paired allocation; no paid fallback, diagnostic probe or model rerun.

This demonstrates one additional successful repair with AST spans under the
same model/attempt budget on this tiny independently authored owned set. It
does not establish real-world accuracy, statistical reliability or commercial
readiness. No fresh Qwen comparison or historical rerun occurred. Historical
Groq remains **1/5 with eight calls**; earlier owned structural Groq remains
**2/4 with six calls** on different material/protocol/budget.

Raw unmodified report, replay and preflight: `evidence/phase4-reliability/owned-pair/`.
Artifact `12391935766` was 13,524 bytes; ZIP SHA-256
`71fb3d0636c591fa1ff116d85706069d99c51c3013e0a07aedfcfabdbc6c390b`.
The ZIP digest, report/source/prompt identities, all usage/call counts and the
replay/report hash binding were checked locally without executing target code.
See `paired-audit.json` and `acceptance.json` for exact per-commit changed files,
commands, results, boundaries and infrastructure.

## Final operational limits

Implemented and verified: opt-in statement repair, stricter bounded iteration,
owned paired evaluation/replay, namespace immutability hardening and a private
metadata-only scope journal. No production deployment or merge, recurring repair,
public offer, customer source/order, private execution or delivery is activated.
Dashboard v11, main, base engineering and synthetic ledger are unchanged; both
PRs remain draft. Existing read-only discovery stays active. No real opportunity
became commercially review-ready.

Remaining gates: independently measured broader real-world repair quality;
private source/dependency isolation and recovery; namespace prototype provenance,
cgroups/syscall/kernel review; approved durable private deployment/backups;
verified source rights and model-sharing consent; fresh verified order/payment;
specific approved commercial terms and delivery. GitHub-hosted namespace checks
remain eight explicit skips despite their actual Codex Cloud acceptance.

Infrastructure actually used: existing Codex Cloud Linux, standard public
GitHub Ubuntu CPU, existing digest-pinned Docker Python and owner-attested Groq
Free Plan. Additional infrastructure spending and purchases: **$0**. Actual
provider entitlement/charges remain independently unverified. No paid service
was enabled; no Stripe request/write, refund, external submission, bounty claim,
customer contact, contract, Mac access or new server. Confirmed received revenue
remains **$0**. Internal **DRY_RUN_READY**; paid work **NOT_READY**.
