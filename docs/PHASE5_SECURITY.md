# Phase 5 execution-boundary validation

The Docker admission boundary remains restricted to the five unchanged historical
excerpts and three fixed owned fixtures. It does not admit an arbitrary repository,
dependency installer, model-selected command, path or network route. Successful
repair verification grants no publication authority.

Phase 5 adds two fixed, owned pressure probes to `verify_runtime_boundary`:

- PID admission starts at most 80 sleeping threads inside the existing 64-task
  cgroup. It requires a denied thread creation and an increased `pids.events:max`
  counter, checks the live task count is at most 64, then releases and joins every
  probe thread. Threads consume cgroup PID slots without a recursive fork bomb.
- CPU admission starts three finite child loops for three seconds under the
  existing one-CPU quota. It requires the kernel's `nr_throttled` counter to
  increase and measures CPU use against elapsed time. It reaps every child;
  the outer ten-second deadline and verified Docker cleanup remain in force.

Both probes use the same digest, flags, read-only mounts, unprivileged UID, dropped
capabilities, seccomp, no-new-privileges, memory and network restrictions as tests.
A missing pressure proof or a failed probe rejects admission. No resource budget
was increased. Existing network, filesystem, memory, output and timeout probes
remain required.

## Executed checks

On 2026-10-21, the managed cloud development environment (Linux 6.18.55,
Docker client/server 28.4.0) ran:

```sh
python -m unittest discover -s tests -p test_curated_docker.py -v
```

All 12 tests passed. The three added tests verify that failed PID pressure rejects
admission, a zero-exit command without CPU proof rejects admission, and measured
pressure counters survive in the evidence result.

An actual `verify_runtime_boundary` call on an exact copy of task 459 ran all
trusted probes without importing or executing the task source. It passed:

| Measurement | Observed |
| --- | --- |
| PID slots at denial | 64 |
| Sleeping probe threads | 63 |
| Cgroup PID denial counter increment | 1 |
| CPU pressure elapsed | 3.035 s |
| CPU time consumed | 3.052 s |
| Throttled CPU periods | 31 |

The complete local result is at
`/workspace/scratch/bf-phase5-pressure-proof.json` for integration into the
engineering evidence. This is local cloud validation, not a GitHub-hosted run.
Existing hosted evidence predates these added pressure probes; a new hosted run
must establish their behavior on the actual Actions runner before calling that
part of admission hosted-verified.

## Dependencies and remaining limits

The admitted historical tests use only the Python standard library in the
digest-pinned official image. The sandbox has no dependency-install step, no
package-manager network access, and no caller-controlled entrypoint. Admission
requires exact historical test bytes and replays source changes through the
existing narrow line validator. Adding dependency files, startup hooks, or other
source files fails the fixed-tree check. Thus dependency resolution, build hooks,
native extensions and unknown test plugins are outside the admitted profile.

Container isolation shares the host kernel. These negative controls do not certify
resistance to unknown kernel/runtime vulnerabilities or arbitrary malicious code.
No full upstream test suite, arbitrary dependencies, cross-platform behavior or
real bounty execution is admitted by this work. Seven legacy namespace/rootfs
checks remain skipped in the broader suite; this change does not claim to have
executed them. Commercial qualification, reproducible safe dependencies and
specific owner authorization remain independent gates.
