#!/bin/sh
# Trusted, explicit offline Linux x86_64 Python 3.13 image build; never run on Mac.
set -eu
[ "$(uname -s)" = Linux ] || exit 3
[ "$(uname -m)" = x86_64 ] || exit 3
[ -x /usr/bin/python3.13 ] || { echo 'Requires distro Python 3.13' >&2; exit 3; }
[ -d /usr/lib/python3.13 ] || exit 3
[ $# -eq 1 ] || { echo 'Usage: build_rootfs.sh /ABSOLUTE/DESTINATION' >&2; exit 2; }
case "$1" in /*) root="$1";; *) exit 2;; esac
[ ! -e "$root" ] || { echo 'Refusing to overwrite rootfs' >&2; exit 2; }
mkdir -p "$root/usr/bin" "$root/usr/lib" "$root/lib/x86_64-linux-gnu" "$root/lib64" "$root/work" "$root/tmp"
cp -L /usr/bin/python3.13 "$root/usr/bin/python3.13"
cp -R /usr/lib/python3.13 "$root/usr/lib/"
for library in libm.so.6 libz.so.1 libexpat.so.1 libc.so.6; do
  cp -L "/lib/x86_64-linux-gnu/$library" "$root/lib/x86_64-linux-gnu/$library"
done
cp -L /lib64/ld-linux-x86-64.so.2 "$root/lib64/ld-linux-x86-64.so.2"
cc -O2 -Wall -Wextra "$(dirname "$0")/capdrop.c" -o "$root/usr/bin/bf-safe-python"
chmod -R a-w "$root/usr"
echo 'Built offline Python 3.13 Linux namespace rootfs. Validate with separate probes before use.'