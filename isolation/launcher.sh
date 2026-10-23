#!/bin/sh
set -eu
root="$1"; src="$2"
# Runs only trusted commands before chroot and drops all host access afterward.
# Permission bits alone do not protect a rootfs owned by the mapped UID: the
# owner can chmod them again after capabilities are dropped. Make the base a
# read-only bind mount inside this disposable mount namespace; /work alone is
# a bounded writable submount. No host mount or global policy is changed.
mount --bind "$root" "$root"
mount -o remount,bind,ro,nosuid,nodev "$root"
mount -t tmpfs -o size=32m,nosuid,nodev tmpfs "$root/work"
cp -R "$src/." "$root/work/"
/usr/sbin/chroot "$root" /usr/bin/bf-safe-python
