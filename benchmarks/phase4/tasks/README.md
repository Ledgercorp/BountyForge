# BountyForge Phase 4 | Five historical Boltons Python repair tasks

These are **curated excerpts**, not complete historical upstream checkouts. Each case includes
unmodified pre-fix function logic from the `26.1.0` tag (or a thin, clearly disclosed
stand-in class for `ThresholdCounter.most_common`), plus new regression tests and controls.

Original upstream project: https://github.com/mahmoud/boltons
Original tagged source: https://github.com/mahmoud/boltons/tree/26.1.0
Source blob references are recorded in `manifest.json`. Upstream copyright belongs to
Mahmoud Hashemi and contributors, under the BSD-style license in `LICENSE.upstream`.

| Case | Original report | Defect | Test scope |
|---|---|---|---|
| 454 | https://github.com/mahmoud/boltons/pull/454 | `args2sh`/`args2cmd` ignore `sep` | 4 excerpt tests |
| 459 | https://github.com/mahmoud/boltons/pull/459 | yottabyte unit unreachable | 3 excerpt tests |
| 460 | https://github.com/mahmoud/boltons/pull/460 | `ThresholdCounter.most_common(None)` broken | 3 excerpt tests, shim |
| 475 | https://github.com/mahmoud/boltons/pull/475 | Unicode separators parsed incorrectly | 3 excerpt tests |
| 524 | https://github.com/mahmoud/boltons/issues/524 | rounded unit stays at 1024 | 4 excerpt tests |

These historical issue URLs establish **benchmark attribution only**. They do not
establish available monetary rewards or currently claimable work. The model prompts are
assembled from symptoms, failing tests and pre-fix source; no reference patch is supplied.

## Execute deliberately

`python benchmark_runner.py` runs only these five vetted local excerpts. It makes no
GitHub writes, makes no paid API calls and does not submit code. It requests the verified
Qwen local endpoint on `127.0.0.1:18080`. Proposed edits are validated against exact
unique original substrings and Python syntax and are applied to disposable copies only.

**Security limitation:** the current benchmark test subprocess uses user/PID/mount/network
namespaces plus resource limits, but does not mount a separate chroot rootfs. That makes
it unsuitable for arbitrary hostile third-party code. The main production worker remains
synthetic-only, and no third-party execution is enabled. Full upstream test suites are
not run, and targeted success (if any) is not full-repository compatibility evidence.

A case is never a success on a model error, malformed JSON, unauthorized path, invalid
syntax, baseline non-reproduction, timeout or failed targeted tests. Successful model
patches are drafts for review, not submissions.