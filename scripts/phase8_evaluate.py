"""Prepare pinned owned Phase8 baselines; live inference is disabled."""
import argparse
import json
from bountyforge.phase8_evaluation import prepare, write_report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True,
                        help='Run fresh owned Docker controls, original baselines and context readiness.')
    parser.add_argument('--selection', help='Trusted explicit selection JSON; requires its exact SHA-256.')
    parser.add_argument('--selection-sha256')
    parser.add_argument('--output', default='evidence/phase8/prepare.json',
                        help='Atomic checkpoint/report path (default: evidence/phase8/prepare.json).')
    args = parser.parse_args(argv)
    if bool(args.selection) != bool(args.selection_sha256):
        parser.error('--selection and --selection-sha256 must be supplied together')
    report = prepare(selection_file=args.selection, selection_sha256=args.selection_sha256,
                     report_path=args.output)
    if args.output:
        write_report(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report['status'] == 'prepared' else 2


if __name__ == '__main__':
    raise SystemExit(main())
