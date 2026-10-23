# Phase 9 — Codex MCP connection acceptance

**Connection status: `CODEX_MCP_SESSION_ONLY`.** Codex's real MCP client
discovered and invoked the BountyForge stdio server in this managed Linux
session. The Codex configuration directory is `/run/codex-environment/codex-home`;
its persistence beyond this execution environment is not established.

## Environment and setup

The checkout was synchronized to `aa0989beea682e16fabcd4c3c1d5ca96928dbfa0`.
PR #1 and PR #2 remained open drafts, and PR #2 still targeted
`engineering/bounded-autonomy-20261020`. The environment is a managed Linux
Codex execution environment with Codex CLI `0.163.0`. Its app-server MCP
status and tool-call methods were used directly; no model turn was started.

Codex registered the server as a stdio MCP using the actual checkout path and
an `env -i` launcher. The launcher gives the Python server only `PATH`; no
GitHub, Groq, Stripe, OpenAI, or other inherited environment variables reach
the server. `codex mcp list --json` showed `bountyforge`, enabled, with stdio
transport. Its configuration resides under `/run`, so it is session-only.

The Codex project-config route was tested in this environment and did not
appear in app-server MCP discovery. Its temporary file was removed. This
session has no persistent Codex Cloud MCP configuration or an always-on
authorized host for remote MCP.

## Codex-originated acceptance

Codex app-server discovered exactly these five tools and their restricted
schemas:

* `bountyforge_status`
* `list_owned_calibration`
* `inspect_owned_calibration`
* `verify_owned_reference`
* `preview_owned_review_package`

All five calls succeeded through `mcpServer/tool/call`. The calibration list
returned four public development fixtures. Inspection of `page-offset-boundary`
returned its defective source without the reference. Verification identified
the repair as preauthored. The package tool returned preview metadata with zero
files written. The status response kept private execution and commercial
authorization false and live repair accuracy unmeasured.

Codex also refused five bounded authorization probes: fake delivery approval,
path traversal, extra customer-source input, an output path, and an unknown
tool. The MCP child process environment contained only the name `PATH`;
environment values were never recorded.

The acceptance harness killed the identified MCP child. Codex reported it
failed, then started it again for a fresh ephemeral Codex thread; a subsequent
status call succeeded. The app-server shut down with exit code 0. The harness
made zero model turns and zero inference calls.

The hosted PR workflow for commit `60a3fbe256efa234d196e8e295af42b8b69aeb77`
also passed: [run 39892577941](https://github.com/Ledgercorp/BountyForge/actions/runs/39892577941)
completed on standard Ubuntu 24.04. The full suite reported 597 tests in
29.112 seconds, with nine skips and no failures. This run did not install
Codex or perform Codex-originated calls; those were separately verified in
the managed Linux session above.

The implementation and acceptance harness are committed at
`60a3fbe256efa234d196e8e295af42b8b69aeb77`. The evidence and cumulative-ledger
update are committed at `eb969bef49f6945e2c6a28b6361bf45c7e293131`.

## Compatibility correction

The first Codex discovery attempt failed because Codex 0.163.0 sends the
standard `_meta.progressToken` field in `tools/list`. BountyForge had rejected
all list parameters as unsupported pagination. A regression test was added;
the server now accepts an object-valued, inert `_meta` field on `tools/list`
and `tools/call`. It still rejects cursors, other fields, non-object metadata,
and authorization claims placed in tool arguments. The existing six stdio
black-box scenarios and two new metadata cases pass.

## Persistence and supported alternatives

OpenAI's Codex MCP documentation describes local stdio configuration and
project-scoped configuration for trusted projects, while warning that local
MCP transports may not be available in Cloud. This running environment's
Codex app-server successfully ran the local stdio server, but the only
effective registration observed here is in its temporary Codex home. The
repository does not claim persistent Cloud registration.

A hosted plugin would need an accessible remote MCP service. Secure MCP Tunnel
requires tunnel permissions, a runtime key, and a tunnel client kept online
inside a host that can reach the MCP server. No persistent authorized host or
tunnel credentials are available here. The GitHub Actions runner is ephemeral;
no public endpoint or tunnel was deployed.

Official references reviewed:

* <https://developers.openai.com/learn/docs-mcp>
* <https://developers.openai.com/plugins/build/plugins>
* <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>

## Boundaries

The owned-only MCP remains separate from the frozen Phase 8 evaluation. No
customer source, payment, delivery, repair inference, or private execution was
used. The existing standalone MCP subprocess suite is not Codex-connectivity
evidence; Codex app-server discovery and invocation above are separate evidence.
No production deployment, merge, external submission, purchase, or customer
operation occurred. Additional spending and revenue remain $0.
