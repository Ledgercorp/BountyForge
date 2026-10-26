# Phase22 — restricted DeepSeek API repair integration

The trusted API broker, bounded credit ledger and owned repair controller are
implemented. Live authentication and current model discovery passed. **No billable
completion has been sent, and DeepSeek repair accuracy is UNMEASURED.** The user
proposed a $2 allocation but explicitly required separate approval before using
credits; no spending grant has been created. Commercial status: **NOT_ADMITTED**.

## Repository and preserved work

Start: `eb9b89dd14c5648236fd7add7a20ddb89db97c70` (Phase21).
Branch: `engineering/phase22-deepseek-api-20261025`, based on draft PR9.
All older draft PRs, main, validators, model defaults, historical candidates,
frozen plans and tests remain intact. Both spent Phase21 plans were revalidated.
The new tasks use the existing explicit supplemental `Catalog` API. Its legacy
`sealed_owned_python_maintenance_supplement` format is a compatibility label;
**these tasks are exposed developmental material, not sealed/unseen evaluation**.
No existing repair engine, source validator or frozen generation file was edited.

## Credential and actual account verification

The exact owner-designated Drive file was read through the authorized connector.
Its permissions/content were not modified. The key was never printed, saved to
a local file, exported in an environment variable, included in an argument,
prompt, receipt, Git commit or GitHub secret. The broker received it through an
inherited anonymous pipe in a short-lived trusted process. The pipe was closed;
the client was closed and the process exited. Python does not promise forensic
memory zeroization; no such guarantee is claimed.

Both the initial controlled metadata check and the implemented broker's own
`inspect` CLI returned authenticated HTTP 200 for `/user/balance` and `/models`.
Across these two checks: **four live read-only API requests, zero completions**.
Both observed a USD balance of **$22.88**, granted **$0.00**, topped-up **$22.88**,
with `is_available=true`. These are observed balances, not a provider spending cap.

Available models: `deepseek-flash` (metadata name DeepSeek-V4.1-Flash) and
`deepseek-v4-pro` (DeepSeek-V4-Pro). Both report 1,048,576 context tokens,
393,216 maximum output tokens, text output, and low/high/max reasoning effort.
Official pricing documentation identifies versions DeepSeek-V4.1-Flash-1017 and
DeepSeek-V4-Pro-0813. API aliases are not cryptographically pinned weight revisions.

The balance and inventory endpoints **do not expose auto-recharge, billing
fallback settings or expiry dates**. No billing setting was changed. The local
activation contract requires explicit owner confirmation that auto-recharge is
disabled and only existing credits may be used. No inference is allowed until
both the spending allocation and that billing gate are satisfied.

Evidence: `evidence/phase22/account-verification.json`,
`broker-account-verification.json`, `provider-specifications.json`.
Official sources:

- https://api-docs.deepseek.com/quick_start/pricing/
- https://api-docs.deepseek.com/api/get-user-balance/
- https://api-docs.deepseek.com/api/list-models/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/thinking_mode/

Reviewed peak cache-miss input/output USD per million: Flash **0.30 / 1.20**;
Pro **1.32 / 3.96**. The estimator assumes no cache/off-peak discount. Reasoning
counts within the completion ceiling. Actual provider usage is parsed separately;
reasoning text is discarded. Provider-invoiced cost is not exposed in this
response schema; computed upper estimates and account-wide balance changes must
remain distinct from provider-confirmed per-request charges.

## Working architecture and security boundary

`phase22_deepseek.py` is a dependency-free trusted outbound HTTPS broker. It has
no listening endpoint. Only the exact `https://api.deepseek.com` origin is used;
GET `/user/balance`, GET `/models`, and a budget-authorized POST
`/chat/completions` are the only allowed method/path pairs. Redirects, arbitrary
URLs/paths, unsupported models, raw POST bypasses, tool calls, credential echoes,
malformed/oversized replies and prompt-embedded keys are rejected. TLS
verification and the Cloud network proxy remain enabled. There are no uploads,
search/fetch tool APIs, SDK session-log uploads or automatic model fallbacks.

The preferred safe route is the existing **external output handoff**, rather than
giving the SDK or a model container API credentials/network access. The model
receives bounded authorized owned source, issue contract, AST edit units and
sanitized failure feedback. It cannot select paths, commands, verifier tests,
repositories, payment authority or delivery. No customer/private source is sent.

`phase22_repair.py` reuses the unchanged supplemental Catalog, scope inference,
AST statement editor, binding/capability/dependency validators, strict Harness
handoff parser, pinned no-network Docker execution and fresh independent replay.
The legacy parser's `CODEX_AGENT` field is an internal transport compatibility
field, **not patch authorship**. Phase22 receipts identify `DEEPSEEK_API`; only
an actual authenticated provider response can support that authorship basis.
No manually authored candidate is a model success.

The SDK's existing 192 MiB limit, model sidecar limits and Qwen defaults are not
changed. The new API route does not start a local model or require SDK egress.
Verifier containers retain the existing read-only root/workspace, no network or
credentials/socket, unprivileged UID, dropped capabilities, seccomp,
no-new-privileges, bounded CPU/memory/PIDs/tmpfs/output/wall time and cleanup.
The existing nine namespace/rootfs skips remain unverified, not passes.

## Credit ledger and activation

`phase22_budget.py` uses a single fixed private local state directory,
`.bountyforge-phase22/`, excluded from Git. SQLite reservations commit with FULL
synchronization **before** the POST. One nonblocking filesystem lock holds the
entire experiment. A grant must match the exact plan and credential fingerprint,
be unexpired, explicitly owner-authorized, confirm existing credits only and
no recharge, approve at most $2 and preserve at least $20. There is no valid grant
in this checkout; `phase22_authorization.example.json` intentionally fails closed.
The private grant file must be owner-only, regular and unlinked elsewhere.

Each task has at most two reservations; the entire experiment at most twelve.
The balance is checked before each reservation. Outstanding unknown reservations
are subtracted conservatively from available headroom; cumulative known upper
cost plus unknown reservations cannot exceed the grant. Timeout, interruption,
malformed/uncertain usage and HTTP errors never automatically refund a request.
Known valid returned usage is accounted even if the proposal is rejected.

The `STOP` file in that private directory prevents new reservations. SIGTERM
interrupts the current request; remote completion after disconnection remains
uncertain. SQLite/lock state survives a process restart. A nonempty ledger blocks
automatic experiment replay and requires reconciliation; deleting it is not a
recovery strategy. This local ledger is **not** cross-workspace/account-global
durable coordination, nor cryptographically authenticated owner consent.
Untrusted model processes cannot access it. Do not launch concurrent experiments
from another workspace or reuse an approval against a different plan/key.

Input estimate: UTF8 serialized messages plus 1,024 framing tokens, capped at
16,384 estimated tokens. Exact provider tokenization is unavailable locally.
Every request reserves the full 16,384-input / 4,096-output envelope at peak,
uncached prices. Returned usage outside that envelope fails closed and retains
the full reservation; a local estimator cannot force provider billing behavior.
This is an application-level control, **not a provider-enforced financial cap**.
No automatic recharge endpoint, purchase or paid fallback is implemented.

## Frozen developmental experiment

Plan: `phase22_experiment.json`, SHA256
`a12648b59de913b18d358e94d2cd6abc482c6c86086765871bf52c8bef27b322`.

Six distinct new owned contracts, each eight tests:

| Task | Intended reasoning |
|---|---|
| discount_checkout | Discount boundary and tax dependency |
| retry_state | Terminal state boundary and backoff |
| merge_records | Falsey identifiers and version precedence |
| response_window | Explicit empty API values and no-content response |
| lease_capacity | Resource release boundary and latest state |
| batch_outcomes | Falsey successful values and exact retry eligibility |

Source, test, selection, provider specification and generation implementation
hashes are frozen. No reference patches were created or supplied. Engineering
Codex can inspect these tests; they are not unseen. The remote repair model gets
only the authorized prompt, not test source or repository-wide access.

Selected experimental model: **deepseek-v4-pro**, thinking enabled/high, JSON
object output, **4,096 maximum output tokens**, **120 seconds per HTTP request**,
one stream at a time, maximum **two generation requests per task / twelve total**.
No separate diagnostic calls. Full stated-envelope peak-price reservation:
**$0.037848 per request**, **$0.454176 across twelve**. These are conservative
estimates under the frozen prices, not observed charges. Pro is a trial selection,
not an evidence-based replacement default or a proven winner over Flash.

The plan requires pricing revalidation after 24 hours. Expired pricing must be
reviewed and a new immutable plan/version approved before any request; do not
silently mutate a plan after inference. Account model/balance metadata are also
checked at activation and balances before each request.

Trusted owner-side commands (credential supplied only through an anonymous pipe):

```sh
python3 -m phase22_run prepare --output /private/path/baselines.json
python3 -m phase22_run inspect --credential-fd FD --output /private/path/account.json
python3 -m phase22_run run --plan-sha256 EXACT_FROZEN_SHA256 \
  --authorization /private/owner-approved-grant.json --credential-fd FD \
  --output /private/fresh-experiment-results
```

Do not create the valid grant until the owner explicitly approves this allocation
and confirms the billing restriction. No credential or approval is uploaded to
GitHub. An API timeout, route error or malformed provider response stops this
initial experiment rather than trying another provider; source-valid but failing
patches get one bounded revision with actual sanitized verification feedback.
Receipts are written after every returned attempt. Successful candidates require
targeted tests and a **fresh independent** Docker replay against unchanged tests.

## Executed verification and confirmed defect

Local full regression: **876 Python tests; 867 passed, nine existing skips,
zero failures**, 32.505s. **31 new focused tests passed**, including actual
SQLite restarts/locks, cumulative/reserve/attempt/total ceilings, malformed and
expired approvals, unknown cost retention, secret echo/prompt handling, restricted
routes, schema/usage checks and real CLI refusal of missing authorization and
unknown customer execution arguments. All **eight Node tests passed**.

Four actual subprocess/HTTP Black Box scenarios passed against a separately
running **local provider simulator**: valid response/accounting, tool-call
rejection after accounting, wall-clock timeout retaining the full reservation,
and redirect refusal without replay. No live inference or model-generated
repairs are implied by these tests. Fake credentials remain test-only.

Actual Linux/Docker acceptance passed: all six failing baselines reproduced
(48 tests executed across six failing suites); a deliberately incorrect candidate
passed source validation but failed its eight required tests, an identical retry
was rejected, a third submission was refused, and unauthorized source/command
proposals were rejected. No authored reference repair was executed. This took
22.050s, 0.155 controller CPU seconds, and 21,602,304-byte controller peak RSS.
These are model-free controller measurements, **not provider compute or latency**.

One confirmed new-adapter defect (**medium severity: failure attribution and retry safety**) was reproduced and fixed: Docker observation
failures were initially caught as source-validator rejections. The adapter now
records `SANDBOX_UNAVAILABLE` / `BLOCKED`, preserves the failure stage and never
labels a blocked verifier as a model reasoning failure or verified result. A
regression test replaces only the external Docker operation; all actual source
validators remain active in that test.

Hosted CI is intentionally model-free: full Python/Node suites, new owned Docker
acceptance, preserved real SDK negative protocol QA with explicitly simulated
responses, and exact recorded Phase20 candidate replay. There are no DeepSeek
secrets, billable jobs, schedules, fresh-model workflow triggers or model downloads.
Hosted conclusions and exact tested commit will be recorded after publication.

## Readiness and next action

Implemented: restricted broker, durable local reservations, activation gates,
six-task frozen experiment, safe retry feedback, independent verifier integration
and model-free acceptance. Verified live: credential authentication, inventory
and balance only. **Actual DeepSeek inference: zero; input/output/reasoning tokens:
zero; model repair accuracy and API inference latency: UNMEASURED.** Provider CPU,
RAM and per-request invoiced spending are not exposed by these API endpoints.

Historical Phase21 Qwen 0/4 per condition and incomplete Granite results remain
unchanged. Different tasks and envelopes preclude a controlled head-to-head claim.
No model default was changed. Additional cash spending **$0**; consumed existing
credits **$0**; confirmed revenue **$0**. No deployment, financial write, customer
work, delivery, external bounty submission, merge or recurring schedule occurred.

Next concrete milestone: explicit owner approval of up to $2 from existing
credits with at least $20 retained, and confirmation auto-recharge is disabled;
then revalidate prices/account, run this bounded trial, publish authentic provider
usage/candidates and independently replay any successful repair. Unseen evaluation,
customer rights/privacy, hostile-code isolation/provenance, cross-workspace private
coordination and commercial payment/delivery/launch authorization remain separate
blockers. Commercial/private execution status remains **NOT_ADMITTED**.

## Final hosted acceptance

Draft [PR10](https://github.com/Ledgercorp/BountyForge/pull/10) preserves PR9 as
its base. Verified implementation commit:
`abaa5feb2357a8c3b8d1fae2aa17805e117a0009`.
[Hosted run 40250087687](https://github.com/Ledgercorp/BountyForge/actions/runs/40250087687)
completed successfully on a standard public Ubuntu runner: **876 Python tests,
867 passed / nine existing skips, zero failures**, 41.058s; **eight Node tests
passed**. All six owned failing baselines and intentional incorrect/repeated/
unauthorized proposal checks passed their expected acceptance behavior.

The preserved real SDK protocol check passed with simulated provider responses,
three runtime audits each refusing all twelve forbidden tools, and clean shutdown
exit 0. The previous recorded Phase20 model candidates reproduced their expected
positive and negative Docker results; these are replay, not new model repairs.
Every hosted step was credential-free and made **zero fresh model requests**.
Hash-bound receipts and run metadata are committed under
`evidence/phase22/github-run-40250087687/`.

The ending evidence-only follow-up commit uses `[skip ci]` to avoid rerunning
unchanged code. No frozen generation source, task, test or spending grant changes
followed the verified implementation. The frozen plan still validates. Main
remains `22250921eb50b7a72e0f474b0f3ff329f81b55a8`; every earlier PR remains draft.
No active Phase22 containers remain, no live grant/reservations exist and the
key remains absent from repository/CI. **Live inference is still blocked by the
explicit spending/billing gate, not by credential retrieval.**
