"""Owner terminal console and CLI for the actual owned dual-engine workflow."""
import argparse
import json
from pathlib import Path
import sys

from bountyforge.repair_engines import (ENGINES, RepairRejected, RepairService,
    RepairUnavailable, engine_inventory, qwen_availability, strict_json, task_inventory)


def emit(value):
    print(json.dumps(value,sort_keys=True,allow_nan=False),flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--interactive',action='store_true',help='Owner engine and task selection menu')
    parser.add_argument('--engine',choices=ENGINES)
    parser.add_argument('--case-id')
    parser.add_argument('--config',help='JSON object with exactly engine and case_id')
    parser.add_argument('--session-stdin',action='store_true',help='Codex-session proposal handoff over bounded JSON lines')
    opts=parser.parse_args(argv)
    try:
        if opts.list:
            if opts.interactive or opts.engine or opts.case_id or opts.config or opts.session_stdin:
                raise RepairRejected('EXCLUSIVE_LIST_MODE')
            emit({'engines':engine_inventory(),'tasks':task_inventory()});return 0
        if opts.config:
            if opts.engine or opts.case_id or opts.interactive:
                raise RepairRejected('AMBIGUOUS_ENGINE_SELECTION')
            path=Path(opts.config)
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1 or path.stat().st_size>1024:
                raise RepairRejected('CONFIG_REJECTED')
            config=strict_json(path.read_bytes())
            if type(config) is not dict or set(config)!={'engine','case_id'}:
                raise RepairRejected('CONFIG_REJECTED')
            opts.engine=config['engine'];opts.case_id=config['case_id']
        if opts.interactive:
            if opts.engine or opts.case_id:
                raise RepairRejected('AMBIGUOUS_ENGINE_SELECTION')
            print('1. Autonomous Qwen\n2. Codex Agent\nSelect engine [1/2]:',file=sys.stderr,flush=True)
            choice=sys.stdin.readline(8).strip()
            opts.engine={'1':'QWEN_LOCAL','2':'CODEX_AGENT'}.get(choice)
            print('Select owned case: '+', '.join(item['case_id'] for item in task_inventory()),file=sys.stderr,flush=True)
            opts.case_id=sys.stdin.readline(66).strip()
        if opts.engine not in ENGINES or opts.case_id not in {item['case_id'] for item in task_inventory()}:
            raise RepairRejected('UNKNOWN_ENGINE_OR_OWNED_TASK')
        if opts.engine=='CODEX_AGENT' and not opts.session_stdin:
            emit({'engine':'CODEX_AGENT','state':'AWAITING_ACTIVE_CODEX_SESSION',
                  'outcome':'CODEX_SESSION_REQUIRED','additional_model_calls':0,'paid_fallback':False,
                  'handoff':'Use prepare_owned_repair and submit_owned_repair through Codex MCP, or --session-stdin.'})
            return 2
        if opts.engine=='QWEN_LOCAL' and not qwen_availability():
            emit({'engine':'QWEN_LOCAL','state':'BLOCKED','outcome':'QWEN_UNAVAILABLE',
                  'additional_model_calls':0,'paid_fallback':False});return 2
        service=RepairService(); task=service.prepare(opts.case_id,opts.engine)
        if opts.engine=='QWEN_LOCAL':
            result=service.run_qwen(task['task_id'],0);emit(result)
            return 0 if result['independently_verified'] else 2
        emit(task)
        revision=0
        for _ in range(2):
            raw=sys.stdin.buffer.readline(3001)
            if not raw or len(raw)>3000 or not raw.endswith(b'\n'):
                raise RepairRejected('CODEX_SESSION_MISSING_OR_INPUT_BUDGET')
            result=service.submit(task['task_id'],revision,strict_json(raw));emit(result)
            if result['state']=='AWAITING_OWNER_APPROVAL':return 0
            if result['state'] in ('BLOCKED','EXHAUSTED'):return 2
            revision=result['revision']
        return 2
    except (RepairRejected,RepairUnavailable,ValueError,OSError,TypeError,RecursionError):
        emit({'state':'BLOCKED','outcome':'OWNED_ENGINE_REQUEST_REJECTED','paid_fallback':False});return 2


if __name__=='__main__':raise SystemExit(main())
