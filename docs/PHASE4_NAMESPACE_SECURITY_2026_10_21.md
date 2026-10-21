# Namespace/rootfs acceptance on current cloud Linux

The seven previously skipped namespace/rootfs checks were actually executed
and **7/7 passed** in the existing Codex Cloud Linux environment. This is a
different machine/policy from the GitHub-hosted Ubuntu runner. No AppArmor,
sysctl, seccomp policy, host capability, runner image or Docker setting changed.
No extra infrastructure, network download, Mac or customer source was used.

The default skip is simply the absent
`BOUNTYFORGE_TEST_ROOTFS/usr/bin/bf-safe-python`; it does not assert that a
namespace has been probed, nor that Python3.13/its library/compiler exist.
A genuinely suitable environment needs Linux x86-64, trusted distro Python3.13
and its libraries, `cc`, `unshare`, mount/chroot tools, and a disposable rootfs.
It must permit the exact unprivileged user/network/mount/PID namespace and UID
map. Root or a privileged container is not required here and was not used.

Current cloud observation: UID1000, kernel6.18.55, effective capabilities0,
seccomp0, max user namespaces39796. AppArmor sysctl/active-LSM paths were absent;
that absence cannot identify a historical runner LSM denial. One exact command,
`unshare -Urnmpf --kill-child /usr/bin/true`, returned0. The known historical
GitHub Ubuntu `/proc/self/uid_map: Operation not permitted` remains a separate
verified denial. Do not retry or weaken that policy expecting this result.

Trusted offline build and reusable acceptance command:

```bash
sh isolation/build_rootfs.sh /tmp/bf-phase4-rootfs-security-20261021
BOUNTYFORGE_TEST_ROOTFS=/tmp/bf-phase4-rootfs-security-20261021 \
  python -m unittest discover -s tests -p test_isolation.py -v
```

That rootfs currently exists for integration reuse. The builder must refuse
an existing destination: do not rebuild over it. It used only local distro
binaries/libraries and repository C source. Compiler warned of unused `argv`;
build completed. Source/runtime hashes and environment facts are in
`evidence/phase4-security/namespace-acceptance.json`.

## Independently found rootfs immutability gap

The original seven checks did not test rootfs mutation. A new owned canary
showed that the mapped owner could `chmod` a rootfs file even with dropped
capabilities. The additional test failed for the expected missing denial.
The launcher now bind-remounts its rootfs read-only **inside the disposable
mount namespace**, then mounts the same bounded writable `/work` tmpfs.
The new test verifies both chmod and write denial and the untouched host
canary. No base capability or execution allowance was expanded.

Two further preflight bugs were reproduced and fixed: resolving a source or
launcher path before checking symlinks erased link identity, admitting links.
Those checks now run first. Noninteger timeouts also fail before execution.
Three unconditional regression methods cover these guards without starting a
namespace. No original test expectation was weakened.

Actual acceptance after hardening: **8/8 namespace checks passed** (2.648s),
including the original seven; **325/325 full tests passed, zero skipped**
(7.493s). Default regression without rootfs: **325 total,317 passed,8 skipped**.
The eighth skip is the newly added rootfs write/chmod probe, not an additional
failed control. Exact original, red and hardened logs are archived.

## Remaining private-execution boundary

This establishes owned Linux security probes, not arbitrary private execution
certification. The generic prototype still lacks immutable rootfs provenance
admission, dedicated cgroup memory/PID/IO controllers, a complete syscall
allowlist/ABI review, exhaustive kernel escape assessment, private source
mutation/recovery guarantees, and dependency admission. No package install or
third-party repository was executed. The production worker is not routed to
this prototype; existing digest-pinned Docker admission is unchanged.

A payment alone still grants no source execution. Private execution, private
persistent intake deployment, customer scope/source/model-sharing permission
and owner-reviewed delivery remain independently gated. No schedule, production
merge, external submission or paid action was performed. Confirmed revenue$0.
