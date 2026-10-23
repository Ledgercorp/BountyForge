"""Separate credential-free process replay of fixed Phase14 Codex candidates."""
import argparse
import json
from pathlib import Path
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.phase12_replay import replay_recording
from bountyforge.repair_engines import receipt_hash


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-sha256',required=True)
    args=parser.parse_args();require_credential_free_host()
    root=Path(__file__).resolve().parents[1];source=root/'evidence/phase14/codex_session.json'
    if source.is_symlink() or not source.is_file() or source.stat().st_size>500000:return 2
    report=replay_recording(source.read_bytes(),args.evidence_sha256)
    report['kind']='phase14_recorded_codex_candidate_independent_replay'
    report['receipt_sha256']=receipt_hash(report)
    (root/'evidence/phase14/codex_independent_replay.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'replay_passed':report['replay_passed'],'cases':len(report['cases']),
                      'new_model_generations':0,'receipt_sha256':report['receipt_sha256']}))
    return 0 if report['replay_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
