"""Inactive owned package CLI; rejects all customer material before any write."""
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bountyforge.patch_review_service import NOTICE, PackageBlocked, build_owned_package
from bountyforge.phase7_owned_demo import canonical

MAX_STDIN_BYTES = 4096


class OwnedParser(argparse.ArgumentParser):
    def error(self, message):
        # Do not echo untrusted customer arguments or material back into logs.
        self.exit(2, f'{NOTICE}: arguments rejected; use --help for the fixed owned package mode\n')


def main(argv=None):
    parser = OwnedParser(description=f'{NOTICE}. Fixed manually authored owned patch package.',
                         allow_abbrev=False)
    parser.add_argument('--owned-only-package', action='store_true', required=True)
    parser.add_argument('--output-dir', required=True)
    received = sys.argv[1:] if argv is None else list(argv)
    if sum(len(arg.encode('utf-8', errors='surrogateescape')) for arg in received) > 4096:
        parser.error('oversized arguments')
    args = parser.parse_args(received)
    if received.count('--owned-only-package') != 1 or received.count('--output-dir') != 1 or len(received) != 3:
        parser.error('ambiguous arguments')
    if not sys.stdin.isatty():
        raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
        if raw:
            print(f'{NOTICE}: stdin rejected; no customer material accepted', file=sys.stderr)
            return 2
    try:
        receipt = build_owned_package(args.output_dir)
    except (PackageBlocked, ValueError, TypeError):
        print(f'{NOTICE}: owned package rejected; private absolute output directory required', file=sys.stderr)
        return 2
    print(canonical(receipt).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
