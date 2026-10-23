"""Manual public-runner entry point for the frozen 20-case Qwen evaluation."""
from __future__ import annotations

import argparse
import json
import sys

from bountyforge.phase8_live_qwen import evaluate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    result = evaluate(output=args.output)
    print(json.dumps({key: result.get(key) for key in (
        'status', 'accuracy', 'inference_calls', 'elapsed_seconds', 'blocking_reason')},
        ensure_ascii=True, sort_keys=True))
    return 0 if result.get('status') == 'completed' and result.get('attempted_cases') == 20 else 1


if __name__ == '__main__':
    sys.exit(main())
