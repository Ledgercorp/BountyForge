"""Read-only namespace-policy diagnostics; never changes policy or retries unshare."""
from __future__ import annotations
import argparse
import json
import os
import platform
from pathlib import Path

PATHS={
 'apparmor_restrict_unprivileged_userns':'/proc/sys/kernel/apparmor_restrict_unprivileged_userns',
 'unprivileged_userns_clone':'/proc/sys/kernel/unprivileged_userns_clone',
 'max_user_namespaces':'/proc/sys/user/max_user_namespaces',
 'process_lsm_profile':'/proc/self/attr/current',
 'active_lsms':'/sys/kernel/security/lsm',
}


def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args(argv)
 observed={}
 for name,path in PATHS.items():
  try:
   with open(path) as f: value=f.read(1024).strip()
   observed[name]={'value':value,'available':True}
  except OSError as exc:
   observed[name]={'available':False,'error':type(exc).__name__}
 status=Path('/proc/self/status').read_text()
 observed['process_controls']={k:v.strip() for line in status.splitlines() if ':' in line
    for k,v in [line.split(':',1)] if k in ('CapEff','CapBnd','NoNewPrivs','Seccomp')}
 report={'kind':'readonly_runner_namespace_policy','kernel':platform.release(),
         'github_runner_image_version':os.getenv('ImageVersion','unavailable'),
         'revision':os.getenv('GITHUB_SHA','local_worktree'), 'observed':observed,
         'policy_modified':False,'unshare_retried':False,'target_code_executed':False,
         'historical_rule_attribution':'original UID-map EPERM is proven; this new snapshot cannot identify a past audit rule'}
 with args.output.open('x') as f: json.dump(report,f,indent=2);f.write('\n')
 print('Read-only runner policy snapshot saved; no namespace bypass or execution')
 return 0

if __name__=='__main__': raise SystemExit(main())
