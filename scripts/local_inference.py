"""Serve only a pre-provisioned pinned profile, credential-free and time bounded."""
import argparse
import json
import time
from bountyforge.local_model_runtime import LocalRuntime
from bountyforge.model_profiles import PROFILES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-profile',choices=PROFILES,required=True)
    p.add_argument('--serve-seconds',type=int,default=120);args=p.parse_args(argv)
    if not 1<=args.serve_seconds<=120:p.error('serve-seconds must be 1..120')
    try:
        with LocalRuntime(args.model_profile) as runtime:
            print(json.dumps({'status':'READY','model_profile':args.model_profile,'port':8080}),flush=True)
            deadline=time.monotonic()+args.serve_seconds
            while time.monotonic()<deadline and runtime.child.poll() is None:time.sleep(1)
        print(json.dumps(runtime.measurement));return 0
    except (RuntimeError,ValueError,OSError):
        print(json.dumps({'status':'BLOCKED','model_profile':args.model_profile,'paid_fallback':False}));return 2


if __name__=='__main__':raise SystemExit(main())
