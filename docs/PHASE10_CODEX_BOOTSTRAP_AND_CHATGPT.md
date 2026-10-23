# Phase 10 — Repeatable Codex MCP and ChatGPT connectivity assessment

**Start:** Phase 9 GitHub SHA `0aa62b33b978dee6f3452ee066c1ec889e6a776d`,
PR #2 draft, Codex MCP session status `CODEX_MCP_SESSION_ONLY`.
**Private execution:** NOT_ADMITTED. **Commercial launch:** not authorized.

## Codex: safe repeatable session bootstrap

Command from a trusted Linux BountyForge checkout:

    python3 -m scripts.bootstrap_codex_mcp --register --verify

Or inspect the current connection without modifying configuration:

    python3 -m scripts.bootstrap_codex_mcp --check

Implementation `scripts/bootstrap_codex_mcp.py` uses Codex's own
`codex mcp add` and `codex mcp list --json` interfaces. It refuses
non-Linux hosts and unknown/competing BountyForge registrations. It is
idempotent for an identical registered server and never edits a Codex
configuration file itself. Its stdio command is anchored to the current
checkout using an absolute Python interpreter path, isolated Python mode
and an `env -i` child launcher exposing `PATH` only.

The optional real-client validation invokes the existing
`scripts.codex_mcp_acceptance` app-server harness. A successful validation
requires five genuine Codex MCP tool invocations, five authorization
refusals, an MCP child with only PATH, no inference and clean app-server
shutdown. This is stronger than `codex mcp list` alone.

The environment reported by Codex 0.163.0 stores MCP registration under
`/run/codex-environment/codex-home`. Nothing in this repository grants
persistent Cloud registration. The bootstrap can be rerun each session,
not scheduled and not guaranteed to execute automatically when Cloud
starts. `AGENTS.md` prompts trusted Codex engineering sessions to run it
when needed. A conflict with an existing named server fails closed;
inspect before manually removing or changing any Codex entry.

The eight synthetic Codex-bootstrap tests use a **fake isolated Codex CLI**
in a subprocess to verify flags, the idempotent add/list workflow, refusal
of foreign registrations, raw environment isolation, sanitized output and
fail-closed acceptance checks. Those tests are not actual Codex Cloud
connectivity. The separate Phase 9 app-server evidence proves that
real Codex discovery and tool calls succeeded in that previous session.

## ChatGPT: read-only investigation of existing infrastructure

An existing personal-tier Hatchable project is already owned by LeftSock:
`LeftSock BountyForge` at
`https://leftsock-bountyforge.hatchable.site`.
It currently has six active unrelated API functions and scan evidence
state. The inspected project has no configured environment secrets,
no deployed MCP endpoint and no verified request authentication suitable
for owner-private ChatGPT access.

Hatchable currently runs the project's deployed APIs as JavaScript V8
functions, not a persistent Python stdio MCP process. In order to use
the public Hatchable domain for a ChatGPT MCP, a separate authenticated
streamable-HTTP adapter would be needed. Simply exposing the owned Python
MCP tools through an unauthenticated public function would violate the
owner-private boundary. **Do not deploy, overwrite or proxy through the
current BountyForge project until independently reviewed authentication,
transport compliance and permissions are established.**

Official supported alternative: Secure MCP Tunnel can privately bridge
the existing stdio server to ChatGPT without a public listener. It still
requires all of the following:

1. An OpenAI Platform tunnel identity and runtime key with appropriate
   organization/workspace permission; never paste the key into chat.
2. An authorized Linux host where the Python MCP server and
   `tunnel-client` can keep running and reach OpenAI over outbound TLS.
3. The ChatGPT custom MCP plugin connection permitted by the workspace.
4. Live Black Box evidence of actual ChatGPT tool discovery and calls,
   including identity, authorization, secret redaction and recovery.

The ephemeral GitHub Actions and Codex Cloud jobs cannot be represented
as a durable always-on tunnel host. No persistent host, tunnel runtime
key or ChatGPT custom plugin connection has been verified or provisioned.
No new paid hosting, public endpoint or production changes were made.

Documentation:
https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
https://developers.openai.com/plugins/build/mcp-server
https://developers.openai.com/plugins/deploy/connect-chatgpt

## Retained safety and measurement distinctions

The currently available five tools are owned/public-only and do not accept
customer code. Verification of a preauthored reference is not a measured
AI-generated repair. Frozen Phase 8 independent model accuracy is still
**unmeasured** (zero new authorized inference calls).

Runtime pinned manifest/config/layer hash integrity remains verified from
Phase 6, but no independent publisher signature/SBOM or private execution
admission is established. Simulated Stripe reviews are not real payments.
No customer rights or delivery approval were granted.

A repeatable Codex session bootstrap is not the same as persistence.
ChatGPT MCP is **NOT_CONNECTED**, pending tunnel or authenticated hosting
and actual connector installation. Revenue remains $0, new spending $0,
Mac not accessed.

## Verified hosted implementation result

[GitHub Actions #39893513956](https://github.com/Ledgercorp/BountyForge/actions/runs/39893513956)
completed successfully at commit
`ce6c961d385cf04ace1b67b153c5b355c638a9ef`:
**605 tests, 596 passed, nine existing skips, zero failures**.
All eight new bootstrap tests passed, including one subprocess which
started the actual BountyForge MCP with only PATH using the isolated
launcher and completed MCP initialize and tools/list.

This was a fake-Codex-registration acceptance test in the GitHub
runner, **not a new Codex Cloud account connection**. The earlier
actual Codex app-server connection from Phase 9 is separate verified
evidence. The next authorized Codex Linux session should run the
session bootstrap once and inspect the result before using its MCP
tools. No GitHub Actions workflow was changed or added.

### ChatGPT private connection checkpoint

Checked connected personal plugin inventory: **no existing BountyForge
private plugin was present**. Existing LeftSock Secret Bridge plugins
were preserved and not repurposed.

An authorized operator can begin checking the applicable Platform
tunnel/workspace permissions at:
https://platform.openai.com/settings/organization/tunnels

Once a real allowed tunnel, restricted runtime key and trusted persistent
Linux host are available, the separate approved tunnel-client installation
and ChatGPT Plugins custom MCP connection may be tested against the five
read-only tools. The previous stand-alone stdio server does not itself
make the tools visible to ChatGPT.

The current authorized chat environment cannot create or run a
persistent tunnel. No tunnel ID or runtime credential was available
through approved connection tools. The existing Hatchable project
remains deployed at its previous version and has **not** been modified
to expose any new MCP route.

**Result:** Repeatable Codex registration CODE_COMPLETE_AND_TESTED,
Codex session persistence NOT_ESTABLISHED,
ChatGPT custom MCP connection NOT_CONNECTED,
private customer execution NOT_ADMITTED, commercial activation DISABLED.
