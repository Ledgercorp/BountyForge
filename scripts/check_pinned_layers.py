"""One-time bounded public image layer SHA/DiffID check. No model or customer data."""
import json
from pathlib import Path

from bountyforge.curated_docker import IMAGE
from bountyforge.oci_runtime_provenance import OCIReviewRejected
from bountyforge.oci_layer_digest import verify_actual_pinned_python_layers


def run_review():
    try:
        report = verify_actual_pinned_python_layers(IMAGE.split('@',1)[1])
        return {'schema':1,'result':'ALL_LAYER_HASHES_VERIFIED',**report,
                'publisher_trust_admitted':False,'private_execution_authorized':False}
    except OCIReviewRejected:
        return {'schema':1,'kind':'public_python_layer_content_review',
                'result':'LAYER_REVIEW_UNVERIFIED',
                'all_compressed_layer_hashes_verified':False,
                'all_uncompressed_diffids_verified':False,
                'publisher_trust_admitted':False,
                'private_execution_authorized':False}


def main():
    out = Path('revenue-evidence/oci-layer-review.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    receipt = run_review()
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('Pinned public Python layers:',receipt['result'])
    return 0


if __name__=='__main__':
    raise SystemExit(main())
