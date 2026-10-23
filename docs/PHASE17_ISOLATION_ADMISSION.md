# BountyForge Phase 17: independent container boundary admission

**Status:** model-free, fail-closed whole-container **probe**. Not an admitted
DeepSeek runtime, production sandbox, new model route, or commercial capability.

## Exact engineering baseline and external references

This branch begins at PR #4 HEAD
\`b5f49c24161c8aec5711709d7caff36ea971879f\`. It does not change
the trusted verifier, the frozen development fixtures, model profiles, or any
prior PR.

The official DeepSeek Harness source inspected at
\`22ddee3792402c3e70ec5f86a63c3e3e895a2f60\`, October 23, 2026:
- [SDK example](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/python/sdk/examples/minimal.py)
- [sdk-minimal Cordis composition](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/packages/bundle/sdk-minimal/cordis.patch.yml)
- [SDK reference](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/python/sdk/README.md)
- [upstream safety notice](https://github.com/deepseek-ai/deepseek-harness/blob/22ddee3792402c3e70ec5f86a63c3e3e895a2f60/SAFETY.md)

Published release pair examined but **not installed, launched or admitted**:
\`deepseek-harness-sdk==0.2.1rc2\` (SDK PyPI wheel SHA-256
\`30fc72c67f20ff4b46c6952087ea596fc70c2692001aa372185a24f9866bdc46\`);
\`deepseek-harness-runtime-bin==0.2.1rc2\` (Linux glibc x86-64 wheel
SHA-256 \`0a0a4eb85a22cd9339972e6a5ced77a27ec791353a5b220e3e10b8cdbbdeca39\`).
Both were published October 17, 2026. Published distribution digests have not
been checked against actual downloaded bytes in this branch. The released wheels
contain native executable code and lack a verified source-to-binary provenance
attestation. **Do not install the native SDK on the trusted GitHub host or infer
that a pin makes it secure.**

## What is actually implemented

\`phase17_isolation.py\` builds a fixed, bounded Docker command, with **no**
input-supplied command, image, sandbox, network endpoint, host mount or runtime
path. It uses the repository's existing verifier image digest:

\`python@sha256:8a00ecb83ed9d0864dfd102a1bdb2067fda907ceb30bb86d09da9ee558b19590\`

It admits only a public standard Linux GitHub runner for this repository after
explicit \`BOUNTYFORGE_PHASE17_PROBE_ACK=1\` and
\`--admit-model-free-probe\`. It runs a **constant**, inspectable Python program
in a new Docker container, not arbitrary developer/customer/model code.

Requested Docker restrictions:

- immutable digest-pinned image with \`--pull=never\`;
- \`--network=none\`, plus a probe for no nonloopback interfaces and failed
  external TCP connect;
- \`--read-only\` rootfs and a **single** read-only private workspace with a
  harmless development canary; no trusted source tree, Docker socket,
  credentials, hidden tests, or home mount;
- \`--cap-drop=ALL\`, default Docker seccomp, \`no-new-privileges\`,
  UID/GID 65534, private IPC and cgroup namespaces;
- one-CPU quota, 192 MiB RAM+swap cap, 32 process maximum;
- only a 16 MiB \`noexec,nosuid,nodev\` writable \`/tmp\` tmpfs;
- fully controlled child environment, bounded stdout, 35-second execution
  timeout and best-effort \`docker rm -f\` cleanup even on error.

Runtime probes must all report affirmative observations of those boundaries,
including cgroup readings and Linux process status. Any missing or false
observation rejects admission. This is a **real constraint probe**, not an
arbitrary hostile-code sandbox certification. It does not prove kernel escape
resistance, multi-tenant isolation, clock/IO quotas, exhaustive file visibility,
reliable cleanup after hard host loss, or isolation of a future Harness binary.

### Reproducible, owner-approved model-free check

The only intended host is a standard public Linux GitHub Actions runner.
\`.github/workflows/phase17-isolation.yml\` runs the existing Python regression,
the focused static tests, pulls the existing digest-pinned public Python image
and invokes:

\`\`\`sh
BOUNTYFORGE_PHASE17_PROBE_ACK=1 python3 -m phase17_isolation --admit-model-free-probe
\`\`\`

No SDK install, model weight, API credential, model call, source patching,
external bounty action, payment, new host or recurring schedule is permitted.
No inference spending occurred.

## SDK and model integration decision

The current DeepSeek Harness \`sdk-minimal\` configuration mounts a persistent
shell with \`danger-full-access\`, a local filesystem provider, and a session
log contributor. The official guide documents optional log uploads with
requests. Removing or disabling tools with profile patches is a useful *second*
layer but **not independent process confinement**; no such patch has been
runtime-tested or authorized by this probe.

An actual Harness run needs an independently provisioned pinned SDK/runtime
image, verified launcher/security profile without model-facing arbitrary shell
tools, fixed trusted IPC and a provider route that is authenticated and
provably $0. \`--network=none\` deliberately precludes remote Groq/DeepSeek
inference inside this probe container. Do not substitute host networking or
give provider credentials to an unconfined model process.

Earlier Groq \`openai/gpt-oss-120b\` requests returned HTTP 403
([record](GROQ_CANARY_403_REVIEW_2026_10_21.md)); the account's live permission,
rate, key scope and remaining $0 quota are unconfirmed. Previously compared
local Qwen/Granite models did not repair their three exposed development tasks.
Neither fact authorizes backend fallback or a paid model request.

Existing PR #4 candidate-file bridge remains the only supported candidate
handoff route. Its real Docker verifier has passed both hardcoded rejection
and a distinct manually written correction, but no model-generated fix has
been verified. BountyForge's default remains QWEN_1_5B.

## Admission interpretation and remaining work

Passing this Phase 17 probe would mean a standard Linux host enforced all
**measured inert-container boundary conditions** for the pinned Python image.
It would not allow DeepSeek Harness to run on that host until equivalent
whole-process controls and third-party SDK supply-chain constraints are
separately tested, including successful denial of SDK tool actions, network
egress and secrets. A future model backend will require actual account-level
$0 admission, model compatibility and a separately bounded live measurement.

**Customer execution, uploads, outreach, payment, commercial admission and
production remain disabled.**


## Controlled native SDK binary bootstrap, no agent inference

A separately gated Phase 17 action uses the publicly released
\`0.2.1rc2\` SDK wheel and matching Linux native runtime wheel. Both files are
downloaded by the trusted runner as **data only**, with no installation
or native-code execution on the host. The \`phase17_sdk_bootstrap.py\`
script verifies their exact PyPI-published SHA-256 digests, rejects symlinks
and unsafe archive entries, bounds decompression, then extracts only the
native runtime payload into a disposable directory.

The native \`dsh\` binary is mounted **read-only into an isolated
no-network Docker container**, alongside the separate read-only
harmless owned-development workspace. It runs exactly:

\`dsh --profile sdk-minimal --dump-default-config\`

The resulting configuration fingerprint is the only output retained. Its
expected default profile includes the \`sdk-jsonrpc-server\`, the
\`persistent-bash\` tool and \`danger-full-access\`; the last two are explicitly
**negative security findings**, so the resulting bundle must not be trusted to
execute uncontained model-generated instructions.

This performs a native CLI *configuration bootstrap*, **not**
\`DeepSeekHarness.run()\`, Python SDK initialization, model API inference,
repair planning, agent tool calls or customer code execution. It must not
be represented as a functioning autonomous DeepSeek agent.

Any CI failure at download, wheel hash, archive extraction, container
launch, profile recognition, quota enforcement or cleanup leaves runtime
and provider admission **blocked**.


## Verified Phase 17 final evidence (2026-10-23)

The final tested source checkpoint is
\`f01b3ba76ba6ec93c6507ed83f528a242d275540\`.
[GitHub Actions run 40034746229](https://github.com/Ledgercorp/BountyForge/actions/runs/40034746229)
completed **successfully**, while explicitly preserving a failed SDK
JSON-RPC initialization as a **blocked admission finding**.

- Focused Docker boundary: **9/9 passed**.
- Focused native SDK and hardened-profile contract: **8/8 passed**.
- Full Python regression: **787 total, 778 passed, 9 existing skips,
  0 failures**.
- Docker inert-probe fields all true: network isolation, root and
  workspace read-only, no host Docker socket, UID 65534, zero effective
  capabilities, no-new-privileges, Docker default seccomp active, cgroup
  limits for 1 CPU/192 MiB/32 PIDs, writable private /tmp, denied external
  TCP route. No customer/foreign source executed.
- Pinned published SDK/runtime wheel SHA-256 digests checked against bytes
  downloaded during the run. The platform-native payload contains
  **322,356,339 uncompressed bytes**; SHA checks do not prove a particular
  source commit produced the native binary.
- Actual native Harness \`dsh\` executable launched inside locked Docker
  in **configuration-only mode**, no model calls. Default profile fingerprint
  \`56feccf005343a895dafccff19abec975a43a9f0f3ed70cb929eef457e5dd1c5\`;
  default profile still includes persistent Bash and danger-full-access.
- The separate fixed local overlay
  \`phase17/hardened-sdk-minimal.patch.yml\` was **applied and composed by
  the installed native runtime** using \`--patch ... --dump-config\`.
  All seven listed shell/filesystem/MCP resource rows were disabled in the
  resulting composition, and the \`session-log-deepseek\` config read
  \`enabled: false\`. Hardened configuration fingerprint:
  \`ede8e425f15724a3eeb1ff01b6c691f3dabb870c90d2ac327e00cd58d951da82\`.
  This is configuration proof, not permission-boundary exploitation testing.
- A separately bounded attempt to start the hardened SDK JSON-RPC
  application and issue **only** \`initialize\` and \`shutdown\` (no
  \`session/prompt\`) **did not initialize**. The native process exited
  code 1 and closed stdout before the handshake responded:
  \`SDK_RPC_STREAM_CLOSED_EXIT_1_DIAGNOSTIC_PROFILE\`.
  The failure category is a sanitized, coarse profile/startup
  classification; the precise underlying plugin/configuration cause has
  **not** been established. Retrying with an interactive Docker stdin
  channel did not resolve it. We did **not** supply a real or fake provider
  credential, enable host networking, relax the container, or call a model.
  This exact observed refusal is recorded as
  \`SDK_RPC_PROFILE_STARTUP_BLOCKED\`, with
  \`initialize_confirmed=false\`,
  \`shutdown_confirmed=false\`, \`agent_turns=0\`, and \`model_requests=0\`.
  New/unexpected failures still cause the CI job to fail.

The initial Phase 17 CI caught a mistyped trusted Docker SHA-256 and stopped;
that typo was corrected, and later isolation tests passed. A separate native
wheel bootstrap encountered an insufficient extraction budget, which was
corrected for the exact hash-verified wheel while keeping a 1 GiB total
uncompressed cap. Both failures remain in immutable Actions history.
Attempts to start the SDK application initially closed the stream even before
interactive Docker stdin forwarding was enabled; the final blocked result
above is the **measured** current state.

### What remains required

The next highest-value engineering task is diagnosing the pinned native SDK
profile startup exit under a **read-only, no-key, network-disabled** Docker
runtime. Verify plugin inject dependencies, required writable runtime paths,
SDK lifecycle and profile fields without weakening the outer containment or
supplying provider credentials.

Then require a credential-free, model-free \`initialize\`/\`shutdown\`
acceptance run with independent refusal probes for forbidden tools.
Only after that, verify actual $0 API authorization and data-handling
permissions for a compatible model. Inference must be bounded separately and
counted explicitly. The previously observed Groq HTTP 403 is **unresolved**.
No DeepSeek-generated repair, blind accuracy measurement, private customer
operation, publishing, payment or revenue claim is admitted.

**Final Phase 17 classification:** isolated native CLI config bootstrap:
\`VERIFIED_DEVELOPMENT\`. Hardened SDK JSON-RPC: \`BLOCKED\`. Model
inference and repair: \`NOT_RUN\`. Commercial execution: \`NOT_ADMITTED\`.
