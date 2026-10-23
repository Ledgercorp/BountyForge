# BountyForge engineering agent notes

This is the engineering branch of a **pre-revenue, owner-private** software
repair project. Do not treat passing owned-fixture tests as authority to
execute customer code, accept money, deliver patches or deploy production.

## Codex Cloud MCP on a trusted Linux checkout

Before work that depends on BountyForge tools, when running inside an authorized
Codex Linux environment with the repo checked out, restore the **session-only**
MCP registration with:

    python3 -m scripts.bootstrap_codex_mcp --register --verify

This does not make Codex Cloud configuration persistent. It safely re-registers
the owned-only stdio MCP in the current Codex home, refuses conflicting
registrations and verifies all five tools through the **actual Codex app-server**
without model turns. If blocked, report the reason; never remove someone else's
MCP registration or overwrite Codex configuration to force success.

The bootstrap deliberately isolates the MCP child environment to PATH.
Never transfer GitHub/Groq/Stripe/OpenAI credentials into the server process.
Do not run on the owner's Mac. Do not assume GitHub Actions has Codex installed.

The original five MCP tools retain their read-only calibration/status behavior.
Phase12 adds explicit engine inventory, fixed owned repair preparation, bounded
Codex-session candidate submission and an explicit QWEN_LOCAL autonomous run.
Task capabilities are revision-fenced and process-local. There are no arbitrary
paths, customer inputs, paid APIs, remote listener or delivery actions. The MCP
child clears inherited variables and uses only a fixed trusted PATH, including
/usr/local/bin for the existing Linux Docker installation.

CODEX_AGENT means this active Codex session authors the candidate through MCP.
Do not start codex exec, SDK inference or another agent turn from inside it.
The app-server helper is only a native MCP transport client and starts no model
turns. No independently authenticated unattended Codex provider is available.
All Phase12 examples are developmental; this agent can read their tests.

See docs/PHASE12_DUAL_ENGINE.md and the local dashboard/repair-console.html.

Phase13 adds eight owned-queue MCP tools; the original ten stay available.
Use create_owned_queue, claim_owned_queue, submit_owned_queue (or the explicit
run_owned_queue_qwen), heartbeat_owned_queue, owned_queue_status,
release_owned_queue and stop_owned_queue. Queue tasks cannot be submitted through
the legacy process-local service. The SQLite store is fixed, local, private and
gitignored; its continuity across a new Cloud workspace is NOT established.
Four batches of up to five jobs, one active lease globally, two claims and two
reserved candidate attempts per job are hard limits. Stop is irreversible for
that batch. Never reset the store to evade its budget during a bounded run.
Use scripts.owned_queue for local owner status/stop and Qwen-only processing.
CODEX_AGENT still requires this active session; never recursively launch a turn.
Phase13 source/tests are exposed development material. See
docs/PHASE13_OWNED_ORCHESTRATION.md for evidence and exact limitations.

Phase14 appends six pinned owned maintenance tasks, without changing the frozen
earlier catalogs or validators. Existing MCP preparation now returns bounded
development assertion feedback and read-only helper context. The autonomous
Qwen retry loop retains only previously source-validated, test-failing sibling
edits, records that transformation and revalidates the complete proposal.
Its native v5 JSON-safe grammar prevents raw delimiter escapes. The original
v2/v3 adapters remain available; the existing
three-change, two-attempt, 150-token request limits remain intact. Codex stays
session-driven. No independently controlled unseen verifier is configured.
See docs/PHASE14_REPAIR_INTELLIGENCE.md; never call these public tasks unseen.

Full details: docs/PHASE10_CODEX_BOOTSTRAP_AND_CHATGPT.md

## Invariants

- Additional infrastructure spending $0.
- No real private customer execution or model-sharing without verified consent.
- No production deployment, merge, public intake, outreach or financial writes.
- Preserve Phase 8 frozen selected 20-case evaluation and core hashes.
- Keep routine PR CI single-trigger, and both existing PRs in draft.
- Do not invent a verified AI repair rate, runtime signature or income.

Phase14 resource-profile evidence proves only a short 7B CPU load/inference
probe. It does not admit 7B as the repair engine or replace pinned 1.5B assets.
Both Phase14 experiments are manual-only after measured runs. Do not reuse
the public development tasks to claim new independent accuracy.

Phase15 adds explicit QWEN_LOCAL profiles: QWEN_1_5B stays default; QWEN_7B is
experimental and rejects rendered prompts above 700 input tokens. Never fall
back across profiles. Existing model/runtime checks now bind endpoint props;
7B requires hard resource caps. The bounded launcher supports explicit 2 or 4
threads only within observed capacity; aggregate CPU cap stays 180 seconds.
Model selection persists in SQLite batches without resetting budgets. Optional
MCP profile arguments are strict enums; CODEX_AGENT has no Qwen model profile.

Four Phase15 measured comparisons produced zero verified repairs. 7B's returned
proposal was source-rejected; its retry hit the CPU cap. Broader comparisons were
resource-blocked, not 0/3 model scores. V9 condition-expression generation was
unit-tested afterward but is unmeasured live. The prepared V5 workflow is manual
only and not scheduled. Preserve every frozen V1–V4 configuration and original
artifact. All cases remain developmental; see docs/PHASE15_MODEL_COMPARISON.md.

Next-generation research adds QWEN35_4B and GRANITE42_3B experimental local model
profiles. QWEN_1_5B is still default; QWEN_LOCAL is the legacy local-engine ID,
while the exact profile/digest identifies the actual author. There is no provider
fallback. Three new owned maintenance cases remain developmental, never unseen.
The manual-only nextgen workflow uses the explicit NEXTGEN_TRIAL envelope:
4 threads, 10GiB AS, 600 aggregate CPU seconds, 240s wall, 75s requests, 256 output
and <=1200 input tokens, two attempts/task, <=18 completion requests total.
Legacy runtime/request defaults remain intact. No runtime replacement is allowed.
Keep the frozen nextgen config/source/test bytes intact after inference. See
/docs/NEXTGEN_MODEL_EVALUATION.md for provenance limitations and measured results.
