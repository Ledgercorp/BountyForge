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

Full details: docs/PHASE10_CODEX_BOOTSTRAP_AND_CHATGPT.md

## Invariants

- Additional infrastructure spending $0.
- No real private customer execution or model-sharing without verified consent.
- No production deployment, merge, public intake, outreach or financial writes.
- Preserve Phase 8 frozen selected 20-case evaluation and core hashes.
- Keep routine PR CI single-trigger, and both existing PRs in draft.
- Do not invent a verified AI repair rate, runtime signature or income.
