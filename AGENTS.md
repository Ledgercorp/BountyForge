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
Its v3 grammar permits at most three physical replacement lines; the existing
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
