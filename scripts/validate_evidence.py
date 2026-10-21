"""Strict separate-reader evidence verifier."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from bountyforge.autonomy import MAX_REPORT_BYTES, verify_envelope


def main(argv=None):
    if not argv or len(argv) != 1:
        raise ValueError('Expected exactly one evidence JSON path')
    file = Path(argv[0])
    if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_REPORT_BYTES + 10000:
        raise ValueError('Invalid evidence file')
    record = verify_envelope(json.loads(file.read_text(encoding='utf-8')))
    print('Evidence accepted; source', record['scan_source'], 'real approvals',
          record['real_review_ready'], 'submissions', record['external_submissions'])
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        print('BountyForge evidence rejected', file=sys.stderr)
        raise SystemExit(2)
