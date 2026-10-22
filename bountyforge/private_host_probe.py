"""Read-only Linux host observations for future private execution review.

A passing host observation is never per-job sandbox admission. Host cgroups
can differ from child cgroups, and no untrusted code is ever launched here.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

FACTS = frozenset((
    'linux_x86_64', 'non_root_uid', 'cap_eff_zero',
    'no_new_privileges', 'seccomp_filter', 'cgroup_v2',
    'memory_max_bytes', 'memory_swap_max_bytes', 'pids_max',
    'cpu_quota_usec', 'cpu_period_usec', 'owned_namespace_probe_passed',
))
BOOLEANS = frozenset((
    'linux_x86_64', 'non_root_uid', 'cap_eff_zero',
    'no_new_privileges', 'seccomp_filter', 'cgroup_v2',
    'owned_namespace_probe_passed',
))
NUMBERS = FACTS - BOOLEANS


class HostProbeRejected(ValueError):
    """Invalid or unsafe host-inspection request."""


def parse_cgroup_max(value):
    if not isinstance(value, str):
        raise HostProbeRejected('Missing cgroup limit')
    stripped = value.strip()
    if stripped == 'max':
        return None
    if not re.fullmatch(r'(0|[1-9][0-9]{0,18})', stripped):
        raise HostProbeRejected('Invalid cgroup limit')
    return int(stripped)


def parse_cpu_quota(value):
    if not isinstance(value, str):
        raise HostProbeRejected('Invalid cpu.max')
    fields = value.split()
    if len(fields) != 2:
        raise HostProbeRejected('Invalid cpu.max')
    quota, period = map(parse_cgroup_max, fields)
    if period is None or period <= 0 or quota == 0:
        raise HostProbeRejected('Invalid CPU quota or period')
    return quota, period


def parse_proc_status(content):
    if not isinstance(content, str):
        raise HostProbeRejected('Invalid proc process status')
    results = {}
    for line in content.splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        if key in ('CapEff', 'NoNewPrivs', 'Seccomp'):
            if key in results:
                raise HostProbeRejected('Duplicate process security status')
            results[key] = value.strip()
    if set(results) != {'CapEff', 'NoNewPrivs', 'Seccomp'}:
        raise HostProbeRejected('Missing process security controls')
    if not re.fullmatch(r'[0-9a-fA-F]{1,16}', results['CapEff']):
        raise HostProbeRejected('Invalid process capability status')
    if (results['NoNewPrivs'] not in ('0', '1') or
            results['Seccomp'] not in ('0', '1', '2')):
        raise HostProbeRejected('Invalid process security flags')
    return (int(results['CapEff'], 16) == 0,
            results['NoNewPrivs'] == '1', results['Seccomp'] == '2')


def assess_host_facts(facts):
    """Compute strict observations. Output never authorizes private execution."""
    if not isinstance(facts, dict) or set(facts) != FACTS:
        raise HostProbeRejected('Unexpected host evidence keys')
    if any(type(facts[k]) is not bool for k in BOOLEANS):
        raise HostProbeRejected('Host boolean evidence type rejected')
    if any(facts[k] is not None and
           (type(facts[k]) is not int or facts[k] < 0 or facts[k] > 10**20)
           for k in NUMBERS):
        raise HostProbeRejected('Host numeric evidence type rejected')
    if facts['cpu_period_usec'] == 0:
        raise HostProbeRejected('Invalid CPU period')

    failed = sorted(k for k in BOOLEANS if facts[k] is not True)
    comparisons = {
        'memory_max_bytes': lambda n: n is not None and 0 < n <= 268435456,
        'memory_swap_max_bytes': lambda n: n == 0,
        'pids_max': lambda n: n is not None and 0 < n <= 64,
        'cpu_period_usec': lambda n: n is not None and n > 0,
        'cpu_quota_usec': lambda n: (n is not None and n > 0 and
                                    facts['cpu_period_usec'] is not None and
                                    n <= facts['cpu_period_usec']),
    }
    for name, check in comparisons.items():
        if not check(facts[name]):
            failed.append(name)
    return {
        'schema': 1,
        'kind': 'read_only_private_host_observation',
        'observed_host_prerequisites_passed': not failed,
        'failed_observations': sorted(failed),
        'private_execution_admitted': False,
        'customer_code_authorized': False,
        'rootfs_provenance_attested': False,
        'source_custody_authorized': False,
        'production_host_admitted': False,
    }


def _read_small(path):
    try:
        with open(path, 'r', encoding='ascii') as stream:
            return stream.read(4097)
    except (OSError, ValueError, UnicodeError):
        return None


def _cgroup_relative_path(raw):
    # A cgroup v2-only process has one mapping "0::<relative path>".
    if raw is None or len(raw) > 4096:
        return None
    fields = raw.strip().splitlines()
    if len(fields) != 1 or not fields[0].startswith('0::/'):
        return None
    path = fields[0][4:]
    parts = path.split('/')
    if any(part in ('.', '..', '') for part in parts):
        return None
    if any('\x00' in part or '\\' in part for part in parts):
        return None
    return parts


def collect_host_facts(*, proc_root=Path('/proc'),
                       cgroup_root=Path('/sys/fs/cgroup'),
                       namespace_probe=False):
    """Only read current process limits, and optionally run unshare with /usr/bin/true.

    No secrets, cgroup paths, hostname, user name, tokens or raw host output
    are returned; this is not safe sandbox admission.
    """
    if type(namespace_probe) is not bool:
        raise HostProbeRejected('Namespace probe must be explicit boolean')
    proc_root, cgroup_root = Path(proc_root), Path(cgroup_root)
    status = _read_small(proc_root / 'self/status')
    try:
        caps, nnp, seccomp = parse_proc_status(status)
    except HostProbeRejected:
        caps = nnp = seccomp = False
    controllers = _read_small(cgroup_root / 'cgroup.controllers')
    cgroup_v2 = controllers is not None and all(
        name in controllers.split() for name in ('cpu', 'memory', 'pids'))
    location = _cgroup_relative_path(_read_small(proc_root / 'self/cgroup'))
    # For v2 at "/" an empty relative path is expected.
    values = {'memory_max_bytes': None, 'memory_swap_max_bytes': None,
              'pids_max': None, 'cpu_quota_usec': None, 'cpu_period_usec': None}
    if cgroup_v2 and location is not None:
        limits_root = cgroup_root.joinpath(*location)
        try:
            for file, key in [('memory.max', 'memory_max_bytes'),
                              ('memory.swap.max', 'memory_swap_max_bytes'),
                              ('pids.max', 'pids_max')]:
                values[key] = parse_cgroup_max(_read_small(limits_root / file))
            quota, period = parse_cpu_quota(_read_small(limits_root / 'cpu.max'))
            values['cpu_quota_usec'], values['cpu_period_usec'] = quota, period
        except HostProbeRejected:
            pass
    namespace_ok = False
    if namespace_probe and platform.system() == 'Linux':
        command = shutil.which('unshare')
        if command == '/usr/bin/unshare' and Path('/usr/bin/true').is_file():
            try:
                result = subprocess.run(
                    ['/usr/bin/unshare', '-Urnmpf',
                     '--kill-child', '/usr/bin/true'],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=4, check=False,
                    env={'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent'})
                namespace_ok = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                namespace_ok = False
    return {
        'linux_x86_64': (platform.system() == 'Linux' and
                         platform.machine() == 'x86_64'),
        'non_root_uid': os.geteuid() != 0,
        'cap_eff_zero': caps,
        'no_new_privileges': nnp,
        'seccomp_filter': seccomp,
        'cgroup_v2': cgroup_v2,
        **values,
        'owned_namespace_probe_passed': namespace_ok,
    }
