# BountyForge rootless Linux isolation prototype

This module **does not authorize arbitrary third-party test execution**. It has passed bounded Linux acceptance probes, but it has not received an independent hostile-code sandbox assessment.

## Tested controls (Python 3.13 x86-64 Linux)

* Unprivileged user, network, mount, and PID namespaces, rootfs chroot. An isolated `/work` tmpfs is mounted at 32 MiB; only preflight-approved files are copied there by a trusted launcher.
* Minimal offline Python standard-library rootfs, no `/proc`, no host repository or credential mounts, no package installers.
* Drop Linux capabilities, set `no_new_privs`, seccomp deny rules for `clone/clone3/fork/vfork`, `socket`, `mount`, `umount2`, `pivot_root`, `ptrace`, `unshare`, and `bpf`.
* RLIMIT CPU=8 sec, virtual memory=512 MiB, per-file write=1 MiB, file handles=64, core dumps=0; parent wall clock timeout 2–30 sec, SIGKILL process group on timeout, new PID namespace terminates child descendants.
* No internet egress, no credential/environment inheritance, no persistent source modifications.

## Known limitations / blocks

* Host cgroup filesystem is read-only, so independent **per-job cgroup memory, pids and IO controllers are unavailable**. RLIMIT_AS is not equivalent to memory cgroup accounting.
* This user namespace sandbox has not been assessed for kernel escape vulnerabilities; namespace+chroot alone are not a security guarantee.
* Seccomp is a narrow syscall denylist, **not** a complete syscall allowlist.
* CPU fixture tests only; no vendor build systems, package installs, real Git checkout or dependency resolution.
* Binary is compiled on the target Linux host from `capdrop.c`; do not copy the compiled binary from an unknown third party.
* No proof that a process running as another host user can be restricted in the same way. Treat the configured rootless map as an environment-specific property.

## Usage (trusted offline Linux environment only)

```bash
sh isolation/build_rootfs.sh /tmp/bf-rootfs-fresh
BOUNTYFORGE_TEST_ROOTFS=/tmp/bf-rootfs-fresh python -m unittest tests.test_isolation -v
```

See `bountyforge/isolation.py` for the programmatic runner. The main worker (`repair_fixture`) is deliberately unchanged and remains synthetic-only. This runner is opt-in.