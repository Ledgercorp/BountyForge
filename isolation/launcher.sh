#!/bin/sh
set -eu
root="$1"; src="$2"
# Runs only trusted commands before chroot and drops all host access afterward.
mount -t tmpfs -o size=32m,nosuid,nodev tmpfs "$root/work"
cp -R "$src/." "$root/work/"
/usr/sbin/chroot "$root" /usr/bin/bf-safe-python