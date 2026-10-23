"""Verify a fixed owned comparison artifact; optional fresh replay, no inference."""
import argparse
import json
import re
from bountyforge.model_comparison_evidence import load_record,summarize,replay_successes
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import ROOT,receipt_hash


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    p.add_argument('--evidence-sha256',required=True);p.add_argument('--replay',action='store_true');args=p.parse_args(argv)
    if not re.fullmatch('[0-9]{1,12}',args.run_id):p.error('Bounded numeric run ID required')
    directory=ROOT/'evidence/phase15';source=directory/('comparison_'+args.run_id+'.json')
    if source.is_symlink() or source.stat().st_nlink!=1 or source.stat().st_size>500000:raise ValueError('Evidence file rejected')
    record=load_record(source.read_bytes(),args.evidence_sha256)
    if record['run_id']!=args.run_id:raise ValueError('Run identity rejected')
    report=summarize(record);report['input_sha256']=args.evidence_sha256;report['receipt_sha256']=receipt_hash(report)
    (directory/('summary_'+args.run_id+'.json')).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    if args.replay:
        require_credential_free_host();replay=replay_successes(record)
        (directory/('replay_'+args.run_id+'.json')).write_text(json.dumps(replay,indent=2,sort_keys=True)+'\n')
        if replay['replay_passed'] is False:return 2
    print(json.dumps({'models':[{'profile':r['model_profile'],'verified':r['verified_repairs']} for r in report['models']],
                      'completion_requests':report['completion_requests_total'],'replayed':args.replay}))
    return 0


if __name__=='__main__':raise SystemExit(main())
