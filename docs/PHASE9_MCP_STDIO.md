# Phase 9 BountyForge MCP: owned-only stdio

**Status: candidate owned-only MCP server, not yet connected to Codex or ChatGPT.**

This adapter is intentionally small. It reuses the Phase 7 public owned
calibration catalog, preauthored reference verifier, Phase 8 inactive
patch-review metadata and previously recorded Phase 6 runtime integrity.
It does not change the frozen Phase 8 twenty-problem evaluation, worker,
model adapter, Stripe client, source custody, sandbox or delivery policy.

## Run in an authorized Linux checkout

From the repository root:

    python3 -m bountyforge.mcp_server

The stdio server speaks newline-delimited MCP JSON-RPC supporting initialize,
notifications/initialized, tools/list, tools/call and ping. Supported protocol
versions: 2025-03-26, 2025-06-18 and 2025-11-25.
All five tools are declared read-only:

1. bountyforge_status: recorded engineering status and non-admission only.
2. list_owned_calibration: metadata for four PUBLIC authored calibration cases.
3. inspect_owned_calibration: only one exact named authored source; no reference solution.
4. verify_owned_reference: execute the exact preauthored owned reference already
   used by the existing Phase 7 development fixture. NOT an AI repair result.
5. preview_owned_review_package: read only the static inactive owned package
   manifest. No artifact writing, customer input, billing or delivery.

The server allows no paths, customer-source uploads, shell commands, URLs,
payment/order tokens, consent claims, model requests or arbitrary changes.
It removes common inherited provider credentials from its own process.
Requests are size and count bounded; JSON duplicate keys, unauthorized
tools, extra argument fields and premature tool invocations are refused.
stdout is protocol-only. Errors are sanitized and do not echo input.

## Codex stdio configuration

On an approved Codex Linux executor containing the checkout, add to Codex's
config.toml (replace the path; do not use the Mac):

    [mcp_servers.bountyforge]
    command = "python3"
    args = ["-m", "bountyforge.mcp_server"]
    cwd = "/absolute/path/to/BountyForge"

The connection still needs an explicit setup action in the actual Codex
environment and independent tools/list verification. This repository commit
alone does not install or enable that Codex connection. Remote Codex
execution may use a different MCP configuration path.

## ChatGPT connection boundary

ChatGPT plugins require a remotely reachable HTTPS MCP server or a
supported Secure MCP Tunnel. A local stdio server cannot be connected
directly from a ChatGPT conversation. No remote transport, bearer-token
security policy, deployment, tunnel or plugin connection is authorized or
implemented in this phase.

References:
https://learn.chatgpt.com/docs/extend/mcp
https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/server/tools.mdx

## Independent Black Box tests

tests/test_mcp_stdio_blackbox.py launches a separate real Python subprocess
and exercises six scenario classes: protocol handshake and discovery; all
five tools; unauthorized arguments/tools; incomplete initialization;
duplicate-key/malformed or oversized JSON; notification behavior and
recovery after unsupported methods. A provider-token sentinel must not
appear in stdout/stderr. These tests are subprocess boundary checks,
not end-to-end remote HTTP, real provider authorization, independent
model repair accuracy or production execution-admission evidence.

## Honest readiness

Owned-only stdio MCP: ENGINEERING_READY_FOR_REVIEW only after hosted checks.
Private code execution: NOT_ADMITTED.
Customer source, paid orders and delivery: NOT_AUTHORIZED.
Model repair accuracy on new frozen suite: unmeasured, zero live calls.
Runtime: content hash verified; publisher signature and signed SBOM unverified.
Additional spending: $0. Real revenue: $0.
Main, draft PR #1, dashboard and synthetic ledger remain untouched.
