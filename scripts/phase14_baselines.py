"""Reproduce pinned owned defects through the existing twenty-control verifier."""
import json
from pathlib import Path
import time
from bountyforge.repair_engines import RepairService, catalog, digest


def main():
    began=time.monotonic();cases=[]
    for spec in catalog():
        if spec['id'] not in {'invoice-summary','event-reducer','cursor-adapter','reading-groups','retry-policy','stock-allocation'}:continue
        start=time.monotonic()
        task=RepairService().prepare(spec['id'],'CODEX_AGENT')
        cases.append({'case_id':spec['id'],'source_sha256':task['source_sha256'],
                      'tests_sha256':task['tests_sha256'],'baseline_feedback':task['baseline_feedback'],
                      'editable_lines':task['editable_lines'],'source_context':task['source_context'],
                      'seconds':round(time.monotonic()-start,3)})
    report={'kind':'phase14_owned_baseline_reproduction','cases':cases,'model_calls':0,
            'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
            'elapsed_seconds':round(time.monotonic()-began,3)}
    target=Path(__file__).resolve().parents[1]/'evidence/phase14/baselines.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'reproduced':len(cases),'model_calls':0,'elapsed_seconds':report['elapsed_seconds']}))
    return 0 if len(cases)==6 else 2


if __name__=='__main__':raise SystemExit(main())
