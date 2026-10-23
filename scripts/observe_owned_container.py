"""Run existing digest-pinned Docker denial probes against ONE trusted fixture."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from bountyforge.curated_docker import IMAGE, MARKER, CuratedSandboxUnavailable, verify_runtime_boundary
from bountyforge.private_boundary_review import OwnedBoundaryRejected,review_owned_docker_proof

def probe_owned_boundary():
    base={'schema':1,'kind':'owned_docker_enforcement_observation',
          'result':'blocked','reason':'probe_unavailable',
          'owned_fixture_only':True,'customer_source_executed':False,
          'model_called':False,'private_execution_admitted':False,
          'rootfs_origin_attested':False,'fresh_payment_verified':False,
          'private_custody_bound_to_runtime':False}
    try:
        if shutil.which('docker') is None:
            return {**base,'reason':'docker_unavailable'}
        pulled=subprocess.run(['docker','pull','--platform','linux/amd64',IMAGE],
           stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL,timeout=100,check=False,
           env={'PATH':'/usr/local/bin:/usr/bin:/bin'})
        if pulled.returncode:
            return {**base,'reason':'pinned_image_unavailable'}
        with tempfile.TemporaryDirectory(prefix='bf-owned-pressure-') as temp:
            root=Path(temp)/'fixture'
            trusted=Path(__file__).resolve().parents[1]/'benchmarks/phase4/tasks/459'
            shutil.copytree(trusted,root,symlinks=False)
            (root/MARKER).write_text('459')
            proof=review_owned_docker_proof(verify_runtime_boundary(root))
        return {**base,'result':'observed','reason':'none',
           'controls_verified':proof['control_count'],
           'docker_image_digest':proof['docker_image_digest'],
           'owned_fixture_controls_passed':True}
    except (CuratedSandboxUnavailable,OwnedBoundaryRejected,TypeError,ValueError,
            OSError,subprocess.TimeoutExpired):
        # Never surface potentially sensitive untrusted exception strings.
        return base

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    output=probe_owned_boundary()
    args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+'\n')
    print('Fixed owned Docker boundary:',output['result'],output['reason'])
    return 0

if __name__=='__main__': raise SystemExit(main())
