"""Emit sanitized, fail-closed Linux runner observations; never run target source."""
from __future__ import annotations
import json

from bountyforge.private_host_probe import (
    HostProbeRejected, assess_host_facts, collect_host_facts,
)


def observe():
    """No namespace launch. The owned-host probe remains a separate opt-in."""
    try:
        facts = collect_host_facts(namespace_probe=False)
        return assess_host_facts(facts)
    except (HostProbeRejected, OSError, ValueError, TypeError):
        return {
            'schema': 1,
            'kind': 'read_only_private_host_observation',
            'observed_host_prerequisites_passed': False,
            'failed_observations': ['observation_unavailable'],
            'private_execution_admitted': False,
            'customer_code_authorized': False,
            'rootfs_provenance_attested': False,
            'source_custody_authorized': False,
            'production_host_admitted': False,
        }


def main():
    result = observe()
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
