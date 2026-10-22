"""One-shot public registry metadata check; no layer downloads or admission."""
import json
from pathlib import Path
from bountyforge.curated_docker import IMAGE
from bountyforge.oci_registry_acquisition import (
    RegistryEvidenceUnavailable, acquire_pinned_python_metadata,
)

def check():
    try:
        evidence = acquire_pinned_python_metadata(IMAGE.split('@',1)[1])
        return {
            'kind':'one_shot_public_python_metadata',
            'result':'METADATA_HASHES_VERIFIED',
            'pinned_reference_digest':evidence['pinned_reference_digest'],
            'pinned_reference_kind':evidence['pinned_reference_kind'],
            'platform_manifest_digest':evidence['platform_manifest_digest'],
            'config_digest':evidence['config_digest'],
            'layer_descriptor_count':evidence['layer_descriptor_count'],
            'compressed_layer_bytes_verified':False,
            'publisher_signature_verified':False,
            'sbom_attestation_verified':False,
            'runtime_execution_admitted':False,
            'commercial_fulfillment_authorized':False,
        }
    except RegistryEvidenceUnavailable:
        return {
            'kind':'one_shot_public_python_metadata',
            'result':'UNAVAILABLE_OR_UNVERIFIED',
            'compressed_layer_bytes_verified':False,
            'publisher_signature_verified':False,
            'sbom_attestation_verified':False,
            'runtime_execution_admitted':False,
            'commercial_fulfillment_authorized':False,
        }

def main():
    target = Path('revenue-evidence/public-runtime-oci.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    observation = check()
    target.write_text(json.dumps(observation,sort_keys=True,indent=2)+'\n')
    print('Pinned public OCI metadata:', observation['result'])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
