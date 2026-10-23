# DeepSeek Harness candidate handoff: limited engineering pilot

**Scope:** output-only, offline, fail-closed adapter. **Not** a running Harness agent.
Baseline: BountyForge PR #2 engineering head at
e578de96cff642a53d4b676bf8aed87955519876 (October 23, 2026).

## Decision and upstream evidence

DeepSeek Harness (MIT, developer preview):
https://github.com/deepseek-ai/deepseek-harness
Upstream master commit inspected: 22ddee3792402c3e70ec5f86a63c3e3e895a2f60.
SDK docs:
https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/python-sdk.md

The public Python SDK exposes DeepSeekHarness.run(...), returning
result.final_response. But the SDK's bundled sdk-minimal profile includes
a persistent shell, a 300-second shell timeout, danger-full-access policy,
and filesystem access outside the selected workspace. It may upload session
logs with model requests and automatically compact context using extra model
requests. Therefore directly spawning this SDK from the trusted BountyForge
controller, interpreting prompts as confinement, or injecting owned source
into an unaudited external endpoint is **not admitted**.

BountyForge has no dedicated independently controlled Harness model route,
sandbox policy proof, or verified $0 inference quota. No SDK/runtime, network
listener, API key, dependency, model weights, or external inference was added.

deepseek-recipe (MIT) handles DeepSeek V4/V4.1-specific encoding and API
conversion but is not a generic upgrade for BountyForge's Qwen or Granite
models. DeepInfer (Apache-2.0) targets NVIDIA SM100/Ascend 950 accelerators
and is excluded from this CPU-bound experiment.

## What the pilot actually implements

bountyforge/deepseek_handoff.py:
- Accepts a string in the shape of Harness Python SDK result.final_response.
- Requires existing CODEX_AGENT session *public prepared-task* identity, exact
  source/test hashes, revision, owned-only subject.py scope, and original
  ast_statement_v1 protocol. CODEX_AGENT here is the existing session transport,
  **not** proof that Codex authored an external Harness output.
- Rejects Markdown fences, extra explanations, duplicate JSON keys, nonfinite
  numbers, unsupported paths/claims/commands, out-of-scope anchors, duplicate
  edits, malformed replacements and oversized output.
- Produces canonical JSON with SHA-256 and explicit
  UNADMITTED_EXTERNAL_CANDIDATE / independently_verified=false fields.
- Never invokes any inference, Bash, network, file mutation, or test executor.

Example using deliberately synthetic prepared-task values (not a real session):

    from bountyforge.deepseek_handoff import prepare_harness_handoff
    prepared = {
        "engine": "CODEX_AGENT", "proposal_protocol": "ast_statement_v1",
        "approved_file": "subject.py", "task_id": "a"*32,
        "case_id": "owned_fixture", "revision": 0,
        "source_sha256": "b"*64, "tests_sha256": "c"*64,
        "editable_lines": [7],
    }
    candidate = prepare_harness_handoff(
        '{"changes":[{"line":7,"new":"return value + 1"}]}',
        prepared,
    )
    assert candidate["admission"] == "UNADMITTED_EXTERNAL_CANDIDATE"

The above only checks the output shape. A synthetic prepared-task dictionary
is **not** sufficient authority to submit or verify anything. For a real owned
task, get prepared values from an actual live RepairService session. An owner
would still need to separately submit candidate["proposal_json"] through the
existing trusted, bounded owned-task submission and independent Docker verifier.
Do not introduce a new public path or automatically map external authorship
to CODEX_AGENT. A valid envelope can still contain invalid Python.

## Verification completed

Local isolated Python 3 unittest run: **18 tests passed, zero errors**, plus
bytecode compile of the new adapter. Tested: valid and canonical output,
multiple edits, duplicate keys, extra payloads, scope violations, malformed
numbers, byte budgets, Unicode edge cases, identity/hash/protocol refusal,
non-string inputs, and preservation of caller data.

This validates only the new offline adapter. It is not a full repository test,
hosted CI result, Harness SDK integration, generated repair, blind evaluation,
or verified security sandbox. No performance or repair-accuracy improvement
has been measured.

## Required before any live Harness trial

1. Obtain an independently admissible sandbox around the **entire Harness
   process** (not merely a selected working directory), deny external network
   and secrets unless separately authorized, and test the confinement.
2. Inspect and pin the actual SDK and runtime versions/dependencies and the
   model backend, including data-handling behavior; establish free quota before
   any inference and do not send private code to unsupported services.
3. Use a fixed owned source snapshot, a disposable checkout, a fresh Harness
   home and no active queue mutation by the Harness process.
4. Preserve BountyForge's existing two-attempt, task/revision/lease bounds;
   independently revalidate every proposal with original source/AST validators
   and the Docker verifier. The current handoff does not perform that step.
5. Compare against the default engine using independent developmental cases,
   accurate spend/resource telemetry, and clear failure reporting. Do not call
   exposed developmental tasks blind evaluation.

**State:** candidate handoff implemented and contract-tested. Harness runtime
integration and measurable repair-quality comparison **not completed**.
Commercial admission remains false; no changes to main, existing drafts,
scheduled workflows, production delivery, payments or customer execution.
