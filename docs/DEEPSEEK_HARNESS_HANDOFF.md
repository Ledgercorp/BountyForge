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

deepseek_harness_handoff.py:
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

    from deepseek_harness_handoff import prepare_harness_handoff
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

## Frozen experiment preservation

The adapter is located at repository root intentionally. The existing nextgen
experiment binds a frozen file inventory of bountyforge/*.py and
scripts/nextgen_comparison.py. Adding a new file under bountyforge/ would change
that inventory and invalidate the frozen experiment even without altering its
behavior. No frozen runtime bytes, manifests, evaluators or comparisons were
changed on this handoff branch.

## Verification completed

Local isolated Python 3 unittest run: **30 focused tests passed, zero errors**, plus
bytecode compile of the new adapter. Tested: valid and canonical output,
multiple edits, duplicate keys, extra payloads, scope violations, malformed
numbers, byte budgets, Unicode edge cases, identity/hash/protocol refusal,
non-string inputs, and preservation of caller data.

This validates only the new offline adapter and mocked verifier handoff. It is not a full repository test,
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

## Follow-on: opt-in trusted verification bridge

`deepseek_owned_bridge.py` is a second **root-level** module. The trusted owner process can hand a previously obtained, bounded Harness `result.final_response` string to `verify_owned_harness_response(service, prepared_task, final_response, allow_owned_verification=True)`. Default flag `False` rejects. It requires:

- The actual existing `bountyforge.repair_engines.RepairService` instance (not an attacker-supplied verifier or model backend).
- A live, unexpired `CODEX_AGENT` task capability from `RepairService.prepare(...)`, checked via its current `_get` fence and revision.
- Exact equality of the preprepared task snapshot and current authoritative task identity, source bytes and digest, test digest, editable scope, state and development-only authorization flags.
- An untrusted output-only proposal accepted by `prepare_harness_handoff`.

Only after all guards pass does it call the **existing** `RepairService.submit`, which applies the normal AST/source validators, owned-only Docker verifier and attempt budget. The bridge wraps the receipt with `UNATTESTED_EXTERNAL_HARNESS_OUTPUT`, preserves any original independent *owned-development* verification result and labels commercial admission `NOT_ADMITTED`. It does **not** attest the DeepSeek model identity. This interface is not an MCP tool, network service, customer API or permission to publish repairs. It deliberately does not instantiate the SDK or expose credentials.

Unit tests additionally cover disabled-by-default handling, exact trusted service type, stale/forged task capabilities, source mutation, invalid candidate refusal, single submission and revision-bound second attempts. These use an instrumented **fake RepairService**; they do not establish live Docker execution or a production-ready Harness runtime.

**Local focused command** (stdlib, no provider/network):

    python -m unittest discover -s tests -p 'test_deepseek*.py' -v

**Result:** 30/30 focused tests passed locally on Python 3, zero additional spending. The rest of the existing repository test suite and hosted CI were **not run** for these new PR #4 files. This bridge is a bounded connection into the trusted verifier, **not** proof of successful DeepSeek-powered repair or the admission of any SDK process. The upstream safety notice explicitly says Harness is developer-preview and unaudited: https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md.

## Hosted offline regression evidence

GitHub Actions check on this PR: [run 40030667610](https://github.com/Ledgercorp/BountyForge/actions/runs/40030667610) against commit `bbe2ee430db7a9f4cc1e010b7d79869725026c6e` completed successfully on `ubuntu-24.04`:

- Focused bridge and handoff: **30/30 passed**, zero errors.
- Entire Python unittest suite: **757 total, 748 passed, nine existing skips**, zero failures.
- No DeepSeek SDK, model inference, Docker execution, provider credentials or deployments were run by this workflow.

These verified results establish integration compatibility with the existing Python regression suite only. No real Harness process has been admitted. Commercial status remains NOT_ADMITTED.


## Owner-operated file handoff and real Docker acceptance (October 23, 2026)

The optional owner-only script `scripts/deepseek_owned_file.py` can accept an
already-generated `result.final_response` JSON file from a **separately
isolated** Harness process. It does **not** install, start or authenticate an
SDK. The caller explicitly selects a member of the frozen LeftSock-owned
development fixture catalog. Example:

```sh
# Candidate output created separately by an authorized, isolated model process.
# Never place real customer source or credentials into this channel.
chmod 600 /absolute/private/path/candidate.json
python3 -m scripts.deepseek_owned_file \
  --case-id weighted-mix \
  --candidate-file /absolute/private/path/candidate.json \
  --admit-owned-development-verification
```

The trusted owner process rejects execution by default without the explicit
flag, then rejects relative/missing/symlink/hardlinked/special files,
group/world-readable files, invalid UTF-8, zero-length or oversized responses,
and changed file bytes. It opens a private regular file using
`O_NOFOLLOW` and `O_NONBLOCK`. Input is not allowed to supply a source path,
command, model, provider, test suite, sandbox, customer repository or worker
executable. No file watcher, recurring schedule or automatic submission exists.

With the explicit flag, `verify_owned_file` prepares a fresh task using the
**real** BountyForge `RepairService` and invokes
`deepseek_owned_bridge.verify_owned_harness_response`, reusing its
authorization, AST statement-scope and independent Docker verifier. Only
sanitized identity, SHA-256, outcome, state and commercial-denial fields are
printed. The results are **owned developmental** observations, never unseen
accuracy evidence or commercial admission. Only run this command on an
authorized Linux Docker host with the existing pinned verifier image.

Hosted validation:

- [Run 40031849725](https://github.com/Ledgercorp/BountyForge/actions/runs/40031849725),
  commit `b4361f7225b3caea8ab0b3063071b88f3d096ada`: real pinned,
  no-network Docker verifier admitted the `weighted-mix` fixture, ran six
  regression tests, correctly rejected a deliberately wrong **hardcoded**
  candidate as `TEST_FAILED`, and refused a stale capability. **No
  DeepSeek/other model call** occurred. 30/30 earlier focused tests and 757
  total Python tests passed (nine skips).
- [Run 40032115992](https://github.com/Ledgercorp/BountyForge/actions/runs/40032115992),
  commit `e7c93bec3ecb937bc4d33cdb83ee9d4fe206f9e5`:
  **43/43** focused handoff/bridge/file-intake tests passed.
  Full suite: **770 total, 761 passed, nine existing skips, zero failures**.
  Digest-pinned Docker rejected the same synthetic patch and ran six tests
  again. CI includes no SDK download, model weight download, model inference,
  customer code execution, external submission or payment.
- The file intake is deliberately a *trusted owner* program. It is **not**
  an untrusted network endpoint and is not itself a whole-process containment
  mechanism for DeepSeek Harness.

### Model/backend admission evidence

A preceding BountyForge Groq trial attempted `openai/gpt-oss-120b` through
the existing Free Plan adapter and got HTTP **403** again even after a
reported permission adjustment
([credential-free review](GROQ_CANARY_403_REVIEW_2026_10_21.md)).
This did **not** measure model repair accuracy or prove the key/permissions
currently work. The hosted provider and billing route remain unadmitted.
Local next-generation Qwen/Granite trials produced 0/3 developmental repairs
each, but that does not establish general accuracy rankings
([study](NEXTGEN_MODEL_EVALUATION.md)).

The upstream DeepSeek SDK's `sdk-minimal` profile still exposes an unrestricted
persistent shell by default; the upstream
[safety notice](https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md)
states it is unaudited. A verified whole-process isolation boundary, SDK
version/dependency pins, confirmed model access, remaining zero-cost quota,
strict egress/data-handling controls and an independent model-quality trial
remain prerequisites to running an actual DeepSeek Harness process.

**Summary:** Candidate output intake → real trusted Docker verification is
implemented and CI-tested. Live DeepSeek Harness inference and autonomous
repair are **not yet admitted or demonstrated**. `QWEN_1_5B` remains the
default; commercial authorization and revenue remain unchanged.
