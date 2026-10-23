"""Verify fixed nextgen artifacts and replay owned candidates without inference."""
import argparse
import json
import re
from bountyforge.model_comparison_evidence import load_record,summarize,replay_successes
from bountyforge.phase8_evaluation import require_credential_free_host
from bountyforge.repair_engines import ROOT,receipt_hash


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True);parser.add_argument('--evidence-sha256',required=True)
    parser.add_argument('--replay',action='store_true');args=parser.parse_args(argv)
    if not re.fullmatch('[0-9]{1,12}',args.run_id):parser.error('Bounded numeric run ID required')
    directory=ROOT/'evidence/nextgen';path=directory/('comparison_'+args.run_id+'.json')
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1 or path.stat().st_size>500000:
        raise ValueError('EVIDENCE_FILE_REJECTED')
    record=load_record(path.read_bytes(),args.evidence_sha256)
    if record['run_id']!=args.run_id or record['kind']!='nextgen_local_model_comparison':raise ValueError('EXPERIMENT_IDENTITY_REJECTED')
    summary=summarize(record);summary['input_sha256']=args.evidence_sha256
    summary['resource_envelope']=record['frozen_experiment']['envelope']
    summary['architecture_effect_independently_measured']=False
    for model,raw in zip(summary['models'],record['models']):
        calls=[c for j in raw['jobs'] for c in j.get('result',{}).get('receipt',{}).get('calls',[])]
        known=[c['metadata'] for c in calls if type(c.get('metadata')) is dict and type(c['metadata'].get('completion_tokens')) is int]
        model['returned_completions_above_legacy_150_tokens']=sum(m['completion_tokens']>150 for m in known)
        model['returned_completion_limit_hits']=sum(m.get('finish_reason')=='length' for m in known)
        model['new_failure_ids_by_attempt']=[a['new_failing_test_ids'] for j in model['cases'] for a in j['attempts']]
    summary['receipt_sha256']=receipt_hash(summary)
    (directory/('summary_'+args.run_id+'.json')).write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    replay=None
    if args.replay:
        require_credential_free_host();replay=replay_successes(record,include_failed=True)
        replay['kind']='nextgen_separate_credential_free_replay';replay['receipt_sha256']=receipt_hash(replay)
        (directory/('replay_'+args.run_id+'.json')).write_text(json.dumps(replay,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'models':[{k:m[k] for k in ('model_profile','tasks_completed','tasks_blocked','valid_patches','verified_repairs','repair_usage')} for m in summary['models']],
        'completion_requests':summary['completion_requests_total'],'replay_requested':args.replay,
        'verified_successes_replayed':replay['verified_successes_replayed'] if replay else None}))
    return 2 if replay and (replay['replay_passed'] is False or replay['failure_reproduction_matched'] is False) else 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,OSError,KeyError,TypeError):
        print(json.dumps({'status':'BLOCKED','outcome':'EVIDENCE_REJECTED','model_calls':0}));raise SystemExit(2)
