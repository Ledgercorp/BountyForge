"""Route this active coding agent's requests through the real Codex MCP client.

The app-server is used only as a transport client: no turn/start, SDK inference,
codex exec, recursive coding agent, provider key or additional model request.
The active Codex session authors proposals between stdin messages.
"""
import json
import argparse
from pathlib import Path
import sys
import time

from bountyforge.repair_engines import strict_json as _load
from scripts.codex_mcp_acceptance import CodexClient, EXPECTED, _owned_child

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/phase12/codex_session.json'


def main():
    global EVIDENCE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase13',action='store_true',help='Write Phase13 evidence without replacing Phase12 records')
    opts=parser.parse_args()
    if opts.phase13:EVIDENCE=ROOT/'evidence/phase13/codex_queue_session.json'
    client=CodexClient(read_timeout=120); began=time.monotonic()
    report={'kind':'phase12_active_codex_session_mcp','client':'Codex app-server MCP client',
            'additional_agent_turns_started':0,'additional_provider_requests':0,
            'active_session_patch_generation':True,'active_session_token_usage':None,
            'usage_note':'Per-candidate active-session tokens are not exposed to the MCP client.',
            'independent_evaluation':False,'classification':'OWNED_DEVELOPMENT',
            'additional_spending_usd':0,'delivery_authorized':False,'calls':[]}
    if opts.phase13:report['kind']='phase13_active_codex_queue_mcp'
    def checkpoint():
        EVIDENCE.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n'
        if len(raw.encode())>500000:raise RuntimeError('Evidence bound exceeded')
        temp=EVIDENCE.with_suffix('.tmp');temp.write_text(raw);temp.replace(EVIDENCE)
    try:
        thread=client.thread()
        servers=client.status(thread).get('result',{}).get('data',[])
        server=next(x for x in servers if x['name']=='bountyforge')
        if server['runtimeStatus']!='connected' or set(server['tools'])!=EXPECTED:
            raise RuntimeError('Configured Codex MCP does not expose current owned tools')
        _,child=_owned_child(client.process.pid)
        if child['environment_names']!={'PATH'}:
            raise RuntimeError('MCP child environment exceeds PATH-only boundary')
        report.update(discovered_tools=sorted(server['tools']),mcp_process_environment_names=['PATH'])
        print(json.dumps({'state':'CODEX_MCP_CONNECTED','tools':sorted(server['tools'])}),flush=True)
        for _ in range(30):
            raw=sys.stdin.buffer.readline(8193)
            if not raw:break
            if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Bounded messages required')
            request=_load(raw)
            if type(request) is not dict or set(request)!={'tool','arguments'}:
                raise ValueError('Explicit tool and arguments required')
            response=client.call(thread,request['tool'],request['arguments'])
            report['calls'].append({'tool':request['tool'],'response':response})
            checkpoint()
            print(json.dumps(response,allow_nan=False),flush=True)
    finally:
        report['app_server_exit']=client.stop()
        report['elapsed_seconds']=round(time.monotonic()-began,3)
        checkpoint()
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,TimeoutError,EOFError,KeyError,StopIteration):
        print(json.dumps({'state':'BLOCKED','outcome':'CODEX_MCP_CLIENT_UNAVAILABLE'}),flush=True)
        raise SystemExit(2)
