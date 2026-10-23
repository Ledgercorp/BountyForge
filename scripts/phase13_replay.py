"""Credential-free replay of the fixed active-session Phase13 recording."""
import argparse
import json
from pathlib import Path
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.phase13_replay import replay_queue_recording

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-sha256',required=True)
    args=parser.parse_args();require_credential_free_host()
    path=ROOT/'evidence/phase13/codex_queue_session.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1 or path.stat().st_size>500000:return 2
    report=replay_queue_recording(path.read_bytes(),args.evidence_sha256)
    (ROOT/'evidence/phase13/independent_replay.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'replay_passed':report['replay_passed'],'cases':len(report['cases']),
                      'model_generation_calls':0,'receipt_sha256':report['receipt_sha256']}))
    return 0 if report['replay_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
