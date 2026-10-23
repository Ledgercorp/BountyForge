"""Explicitly labeled owned-only order simulation CLI; never real Stripe intake."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from bountyforge.phase8_synthetic_order import (SESSION, SCENARIOS, SimulatorStripeGate,
    SimulationRejected, SyntheticOrder, SyntheticBlocked, initialize, independent_verify,
    result, serve_provider)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Synthetic order arguments rejected\n')


def main(argv=None):
    parser=Parser(add_help=False)
    commands=parser.add_subparsers(dest='command',required=True,parser_class=Parser)
    init=commands.add_parser('init',add_help=False); init.add_argument('--root',type=Path,required=True)
    provider=commands.add_parser('provider',add_help=False)
    provider.add_argument('--scenario',choices=SCENARIOS,default='paid')
    commands.add_parser('verify-owned',add_help=False)
    run=commands.add_parser('run',add_help=False)
    run.add_argument('--root',type=Path,required=True); run.add_argument('--port',type=int,required=True)
    run.add_argument('--scope-ttl',type=int,default=300)
    run.add_argument('--stop-after',choices=('payment','scope','proposed','verified','packaged'))
    run.add_argument('--pause-after-scope',action='store_true')
    hold=commands.add_parser('hold',add_help=False); hold.add_argument('--root',type=Path,required=True)
    hold.add_argument('--reason',choices=('revoked','cancelled'),required=True)
    args=parser.parse_args(argv)
    order=None
    try:
        if args.command=='provider': serve_provider(args.scenario); return 0
        if args.command=='verify-owned': print(json.dumps(independent_verify(),sort_keys=True)); return 0
        if args.command=='init': output=initialize(args.root); code=0
        elif args.command=='hold':
            order=SyntheticOrder(args.root); output=order.hold(args.reason); code=0
        else:
            raw=sys.stdin.buffer.read(257)
            try: request=json.loads(raw)
            except ValueError: request=None
            if len(raw)>256 or request!={'session_id':SESSION}:
                raise SimulationRejected('invalid_session')
            gate=SimulatorStripeGate(args.port)
            order=SyntheticOrder(args.root,scope_ttl=args.scope_ttl)
            code,output=order.run(gate,stop_after=args.stop_after,pause_after_scope=args.pause_after_scope)
    except (SimulationRejected,SyntheticBlocked) as exc:
        reason=str(exc) if isinstance(exc,SimulationRejected) else 'workspace_rejected'
        output=result(status='rejected',state='BLOCKED',reason=reason); code=2
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,sqlite3.Error):
        output=result(status='rejected',state='BLOCKED',reason='operation_unavailable'); code=2
    finally:
        if order is not None: order.close()
    print(json.dumps(output,sort_keys=True))
    return code


if __name__=='__main__': raise SystemExit(main())
