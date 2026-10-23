# Phase 8 independent Black Box acceptance — 2026-10-23

Final targeted acceptance: **28 tests passed**: 8 independent Black Box tests,
14 existing real-process commercial scenarios, and 6 service CLI cases. One
reproduced workspace-validation defect was fixed by the commercial implementation
agent and independently retested. Commercial success remains
`AWAITING_OWNER_APPROVAL`; real payment, owner consent, customer rights, customer
execution, delivery and model calls remain disabled/false/zero.

The audit used the Black Box skill's reproduce-before-fix workflow. Work occurred
only in `/workspace/BountyForge-blackbox-phase8`, based on `f55ad34`, with service
`3b23a5033bb5d9cb0dca0ef7f48af5f68ff2f5a5` and commercial `8162870` integrated.
No application implementation was authored by this audit. The independent tests
import no application functions; they drive actual Python CLI processes, private
files, independent SQLite connections and real numeric-loopback HTTP processes.

## Confirmed defect and regression

- **Severity:** medium availability defect and violation of the documented
  private, regular, single-link workspace-file invariant. No observed owner-file
  data loss, payment bypass, execution authorization or delivery authorization.
- **Observed defect:** an allowed SQLite rollback journal was not validated
  before SQLite opened the database. A FIFO blocked the real coordinator beyond
  the three-second acceptance deadline. Public-mode and hardlinked journal files
  were accepted, and the order reached `AWAITING_OWNER_APPROVAL`.
- **Reproduction:** initialize an empty private rehearsal root; start the owned
  HTTP provider; submit the exact fixed order with `--stop-after payment`; create
  `phase8.SIMULATION_ONLY.sqlite3-journal` as a 0600 FIFO, a 0644 empty regular
  file, or a hardlink to an owned 0600 sentinel; submit the same fixed order.
  FIFO timed out; the other two returned status 0 instead of rejecting the
  workspace. The hardlinked owner sentinel remained byte-identical.
- **Root cause:** the workspace check permitted the journal's filename and
  rejected symlinks but did not check its file kind, permissions, link count or
  bounds before `sqlite3.connect`.
- **Fix:** implementation commit `040eefab11750241a63b0c6c1bf089cbf02ff8bf`
  adds metadata-only validation of every existing allowed workspace file before
  lock/database access and again while holding the worker lock. It rejects unsafe
  file kinds, ownership, modes, multiple links and excessive size without opening
  a FIFO. This was integrated locally as `1cb672b`.
- **Regression:** test-only commit `45514ec` reproduced three failures before the
  fix; the same three real-process tests pass after it, with zero provider
  requests and unchanged database bytes. Expanded test-only commit `6e3efe3`
  adds five adjacent acceptance tests and an independent recording provider.
- **Patch audit:** the implementation change is confined to workspace metadata
  admission. Payment validation, owned repair bytes, ledger transitions,
  authorization flags and disabled delivery routes are unchanged. The prior
  successful, recovery and rejection scenarios all passed after the fix.

## Process and protocol results

| Scenario | Result and observed evidence |
| --- | --- |
| Healthy owned simulation and duplicate | PASS: six then three actual provider GETs; one then zero independent owned replays; one job; identical package hash and unchanged reviewed workspace on duplicate. |
| Independent HTTP oracle | PASS: nine recorded requests use exactly the three fixed resource paths, loopback peers, nine fresh nonces, and no Authorization header. Observed provider mutation requests: zero. |
| Receipt, artifact and durable-state agreement | PASS: SHA-256 of package bytes matches receipt and SQLite; contiguous five-event history; both simulation evidence hashes match independently read records. |
| Incomplete, invalid and customer-shaped requests | PASS: empty, malformed, null/list/object, extra JSON, extra source field, wrong identifier and oversized stdin fail before provider requests; existing reviewed bytes remain exact. Service rejects source/path/execution/delivery/verification flags and all nonempty stdin. |
| Payment rejection and transport faults | PASS: unpaid, underpaid, cancelled, disputed, refunded, invalid-session, nonce replay, provider outage, malformed/oversized/redirect/error HTTP replies; no verified/delivered claim. |
| Late payment/scope changes | PASS: refund before final review and expiry during final provider reads prevent packaging; expiry, revocation and cancellation remain terminal holds. |
| Retained package/proof and SQLite corruption | PASS: package corruption rejects; externally edited event hash rejects before any more HTTP or workspace change; corrupted retained proof becomes durably HELD without another replay, and restoring the proof does not restore authority. |
| Interruption and restart | PASS: real killed commercial worker resumes the committed scope checkpoint without another job; payment/proposed/verified/packaged checkpoints recover. A service killed while awaiting stdin EOF writes nothing and later restarts successfully. |
| Service duplicate and corrupt existing package | PASS: second generation refuses to overwrite the package, including corrupted bytes, and preserves an unrelated owner file. This is nonoverwrite evidence; corruption-verifier API coverage is separate. |
| Unauthorized approval/delivery/customer execution | PASS: corresponding external commands/flags are rejected; all receipt authority fields remain false. |

The final command
`python -m unittest tests.test_phase8_blackbox tests.test_phase8_synthetic_order_process -v`
ran **22 tests in 11.151 seconds, all passing**. Separately, the six service
process cases passed: success, unknown/customer/deceptive flags, missing/help,
duplicate/oversized/invalid output arguments, direct-script invocation, and
nonempty/oversized stdin. `git diff --check` passed. The broader repository suite
was not rerun by this independent audit.

No unhandled application traceback/panic or secret leakage was observed in these
cases. The original FIFO hang was terminated by the test harness; it is fixed in
the tested revision. All subprocess providers/workers were stopped and temporary
workspaces removed. Cost and observed revenue were $0. No production credentials,
live Stripe/Groq, customer inputs, deployments, financial actions, Mac access or
external communications were used.

## Limits and rejected suspicions

This proves the fixed owned simulation and the separate owned service CLI under
the tested local process/filesystem/HTTP conditions. It does not establish real
Stripe TEST integration, authenticated payment provenance, customer intake,
customer-code isolation, live model effectiveness, production readiness, owner
approval or delivery authority. The richer service package and commercial
simulation package use their separate documented entrypoints.

Model-unavailable, generated-invalid-patch and generated-test-regression cases
cannot be injected through either external Phase 8 CLI: neither accepts a model,
patch, test command or runner. They are **unsupported at this boundary**, not
reported as passes. The repair-core API requires a runner and is a separate
acceptance surface; this audit did not replace external acceptance with direct
internal calls. The service integrity verifier is also an API, not an exposed
CLI, so this audit does not claim an external verifier rejection test.

The suspected hardlink owner-file corruption was rejected: the sentinel stayed
exact in the pre-fix reproduction. The service's open-stdin wait was also
rejected as a defect because its documentation explicitly requires EOF/input;
killing and restarting that process preserved the expected files. A valid
duplicate did not rewrite reviewed state or rerun the independent repair. An
owner coherently rewriting the whole database/artifact set, malicious concurrent
filesystem replacement and real power-loss durability remain outside the tested
rehearsal boundary.
