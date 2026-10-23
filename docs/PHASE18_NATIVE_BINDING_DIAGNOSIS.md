# BountyForge Phase 18: native-binding startup diagnosis

**Classification:** SDK server startup BLOCKED. No model requests, no customer code, no commercial admission.

## Frozen baseline and source

- Branch base: Phase 17 PR #5 `60f7d9f831db379e55a844bb7e8652c2bfa38bc5`.
- Pinned SDK: `deepseek-harness-sdk==0.2.1rc2`, SHA-256 `30fc72c67f20ff4b46c6952087ea596fc70c2692001aa372185a24f9866bdc46`.
- Pinned native runtime: `deepseek-harness-runtime-bin==0.2.1rc2`, SHA-256 `0a0a4eb85a22cd9339972e6a5ced77a27ec791353a5b220e3e10b8cdbbdeca39`.
- Actual running native application comes only from the hash-verified runtime distribution within Phase 17's established read-only, no-network, UID-65534, capabilities-dropped Docker container.
- The `--patch ... --dump-config` hardened profile was previously validated, with shell/terminal/filesystem/MCP tools disabled and session-log upload disabled. Configuration composition is **not** proof that the application can boot.

## Specific observed startup defect

[Actions run 40037044116](https://github.com/Ledgercorp/BountyForge/actions/runs/40037044116) executed an exact, model-free native SDK initialization attempt with additional allowlisted/error-redacted diagnostics. The process closed JSON-RPC stdout with exit code 1, **before any initialization response**. Its 1,472-byte startup stderr (not disclosed raw) contained:

```
error: dsh: host preparation failed: no usable native binding found for opaque (auto)
at boot ...
[cause]: error: no usable native binding found for opaque (auto)
at NoUsableBindingError ...
at loadEntry ...
at createEntryApi ...
```

Native dependency loading, rather than a provider request, is the confirmed *failure stage*. The precise reason the native binding is unusable (missing platform file, binary ABI incompatibility, executable carrier not reporting an entry package identity, or inaccessible native path) remains unproven.

For a controlled, no-secret hypothesis check, `NARB_DISABLE_NATIVE_CACHE=1` (documented by the upstream [native loader packaging guide](https://github.com/deepseek-ai/dsh-node-addon-require-builtin/blob/master/docs/packaging.md)) was passed **only** to the already-contained native server. [Actions run 40037284472](https://github.com/Ledgercorp/BountyForge/actions/runs/40037284472) produced the **same** exit code, redacted error and SHA-256 of captured stderr `6fd52d4214eeb7c98d1e5957358a66dd2e12bbab9b650c2c3d69703f4e1cdefe`. This does **not** establish that the only problem is executable `/tmp`, and provides no evidence that weakening `noexec` would help. The ineffective cache override was reverted.

The upstream [DeepSeek native addon architecture](https://github.com/deepseek-ai/dsh-node-addon-require-builtin/blob/master/docs/architecture.md) describes `node-addon-native-custom-loader` resolving platform-matched optional `.node` packages and failing closed without a usable binding. Published bindings may depend on the Node/V8 fingerprint and package resolution. The observed `opaque (auto)` discriminator is unusual and merits upstream-package-specific verification; **do not infer a reliable workaround from this text alone**.

## Engineering changes

- `phase17_sdk_bootstrap.py`: sanitized, strictly bounded stderr classifier (never emits raw text; paths, email-like values and opaque tokens redacted); native loader error classification `SDK_RPC_STREAM_CLOSED_EXIT_1_DIAGNOSTIC_NATIVE_BINDING`. The known failure remains `SDK_RPC_PROFILE_STARTUP_BLOCKED`; all other failure stages continue failing CI.
- `tests/test_phase17_sdk_bootstrap.py`: tests sanitization, rejects non-byte logs, recognizes explicit native addon failure and prevents confusion with source or provider errors.
- `.github/workflows/phase18-sdk-startup.yml`: a separate, manually uncredentialed, PR-only GitHub Linux workflow with a fixed matching SDK/runtime wheel pair, frozen digest-pinned verifier image, the existing Docker constraints, zero model calls and cleanup. It does not download/model-install inference weights.

**Key distinction:** A green CI run with `SDK_RPC_PROFILE_STARTUP_BLOCKED` means the diagnostic and boundary checks behaved as specified. It is *not* a green live SDK initialization.

## Next technical admission test

The next plausible route is a separately **version/digest-pinned official Node CLI and matching native optional-addon package set** staged as data and run only inside an equivalently isolated container. Before launching it, validate exact platform package presence, binary hashes and Node ABI compatibility for Linux x64 glibc. Do not install arbitrary packages or their scripts on the trusted host. Do not disable `noexec`, grant network access to the model process, patch Node internal loader calls, or bypass failed native checks merely to gain a green result.

If the alternative cannot be securely admitted, preserve this as an upstream native runtime packaging blocker and stop actual SDK execution.

No authenticated Groq model access is established (previous HTTP 403). Model requests, verified model-generated repairs and commercial authorization stay **zero / zero / NOT_ADMITTED**. No Mac or paid infrastructure was used.

## Final hosted Phase 18 acceptance

[GitHub Actions run 40037480239](https://github.com/Ledgercorp/BountyForge/actions/runs/40037480239) succeeded on tested code commit `f83c76890a80080a94ae7cbfdc0e6267754e3d40`. Its success signifies that the fail-closed diagnostic and the existing containment held, **not** that the live native SDK server was admitted.

- Focused pinned SDK contract tests: **9/9 passed**.
- Complete Python regression: **788 total; 779 passed, nine existing skips, zero failures**.
- Existing digest-pinned Python Docker boundary freshly validated: all 14 required observations true, including no-network, unprivileged UID, no new privileges, no writable workspace and 1 CPU / 192 MiB / 32 PID restrictions.
- Published SDK `0.2.1rc2` and matching Linux runtime wheel bytes were hash-checked again; native default/hardened profile configuration-only launch succeeded, hardened tool rows and log-upload denial recognized.
- Actual native JSON-RPC `initialize` **still failed** before a response; classified `SDK_RPC_STREAM_CLOSED_EXIT_1_DIAGNOSTIC_NATIVE_BINDING` with `SDK_RPC_PROFILE_STARTUP_BLOCKED`. Its server invocation reported process exit code 1; provider model requests, agent turns, earned income and verified AI-written repairs **zero**. No SDK forbidden-tool runtime probes were admitted because the session never initialized.
- No trusted verifier modifications, no locally connected Mac, no new infrastructure provisioning, no credential exposure or billable inference. New spending controlled at $0, without independent account-invoice audit.

The next step is therefore a separately admitted Node CLI/runtime package layout probe for the published native addon, not retrying Groq or loosening isolation. See the native loader documentation referenced above.
