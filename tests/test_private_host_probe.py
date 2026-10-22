"""Offline host policy/read-only Linux evidence; no customer-code execution."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bountyforge.private_host_probe import (
    HostProbeRejected, assess_host_facts, collect_host_facts,
    parse_cgroup_max, parse_cpu_quota, parse_proc_status,
)


GOOD = {
    'linux_x86_64': True,
    'non_root_uid': True,
    'cap_eff_zero': True,
    'no_new_privileges': True,
    'seccomp_filter': True,
    'cgroup_v2': True,
    'memory_max_bytes': 268435456,
    'memory_swap_max_bytes': 0,
    'pids_max': 64,
    'cpu_quota_usec': 100000,
    'cpu_period_usec': 100000,
    'owned_namespace_probe_passed': True,
}


class HostProbeTests(unittest.TestCase):
    def test_every_observed_boundary_can_pass_without_authorizing_execution(self):
        report = assess_host_facts(GOOD)
        self.assertTrue(report['observed_host_prerequisites_passed'])
        self.assertEqual(report['failed_observations'], [])
        for field in ('private_execution_admitted', 'customer_code_authorized',
                      'rootfs_provenance_attested', 'source_custody_authorized',
                      'production_host_admitted'):
            self.assertFalse(report[field])
        self.assertEqual(report['kind'], 'read_only_private_host_observation')

    def test_every_required_observation_is_fail_closed(self):
        fields = [key for key, value in GOOD.items() if isinstance(value, bool)]
        fields += ['memory_max_bytes', 'memory_swap_max_bytes', 'pids_max',
                   'cpu_quota_usec', 'cpu_period_usec']
        for field in fields:
            changed = dict(GOOD)
            changed[field] = (None if type(changed[field]) is int else False)
            with self.subTest(field=field):
                report = assess_host_facts(changed)
                self.assertFalse(report['observed_host_prerequisites_passed'])
                self.assertIn(field, report['failed_observations'])
                self.assertFalse(report['private_execution_admitted'])

    def test_malformed_facts_are_rejected_not_copied_to_public_evidence(self):
        for facts in ({}, dict(GOOD, cap_eff_zero='yes'),
                      dict(GOOD, memory_max_bytes=True),
                      dict(GOOD, strange_secret='s3cr3t'),
                      dict(GOOD, cpu_period_usec=0)):
            with self.subTest(facts=list(facts)), self.assertRaises(HostProbeRejected):
                assess_host_facts(facts)

    def test_cgroup_limits_and_cpu_quota_are_bounded(self):
        self.assertEqual(parse_cgroup_max('268435456\n'), 268435456)
        self.assertIsNone(parse_cgroup_max('max\n'))
        self.assertEqual(parse_cpu_quota('100000 100000\n'), (100000, 100000))
        self.assertEqual(parse_cpu_quota('max 100000\n'), (None, 100000))
        for payload in ('-2', 'garbage', '10 extra', '00000000000000000000000'):
            with self.subTest(payload=payload), self.assertRaises(HostProbeRejected):
                parse_cgroup_max(payload)
        for payload in ('max max', '0 100000', '1000 0', '1000', '10 20 30'):
            with self.subTest(payload=payload), self.assertRaises(HostProbeRejected):
                parse_cpu_quota(payload)

    def test_proc_self_status_parse_rejects_missing_privilege_fields(self):
        valid = 'CapEff:\t0000000000000000\nNoNewPrivs:\t1\nSeccomp:\t2\n'
        self.assertEqual(parse_proc_status(valid),
                         (True, True, True))
        self.assertEqual(parse_proc_status(valid.replace('Seccomp:\t2', 'Seccomp:\t0')),
                         (True, True, False))
        with self.assertRaises(HostProbeRejected):
            parse_proc_status('CapEff:\t0000000000000000\n')

    def test_collector_never_discloses_cgroup_paths_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / 'proc'
            cgroup = root / 'cgroup'
            (proc / 'self').mkdir(parents=True)
            (cgroup / 'hidden-subscriber-id').mkdir(parents=True)
            (proc / 'self/status').write_text(
                'CapEff:\t0000000000000000\nNoNewPrivs:\t1\nSeccomp:\t2\n')
            (proc / 'self/cgroup').write_text('0::/hidden-subscriber-id\n')
            (cgroup / 'cgroup.controllers').write_text('cpu memory pids')
            limits = cgroup / 'hidden-subscriber-id'
            for name, data in {'memory.max': '268435456',
                               'memory.swap.max': '0', 'pids.max': '64',
                               'cpu.max': '100000 100000'}.items():
                (limits / name).write_text(data)
            with patch('bountyforge.private_host_probe.platform.system', return_value='Linux'):
                with patch('bountyforge.private_host_probe.platform.machine', return_value='x86_64'):
                    with patch('bountyforge.private_host_probe.os.geteuid', return_value=1000):
                        facts = collect_host_facts(
                            proc_root=proc, cgroup_root=cgroup,
                            namespace_probe=False)
            self.assertEqual(facts['memory_max_bytes'], 268435456)
            self.assertFalse(facts['owned_namespace_probe_passed'])
            self.assertNotIn('hidden-subscriber-id', str(facts))
            self.assertFalse(assess_host_facts(facts)['private_execution_admitted'])

    def test_namespace_probe_never_runs_untrusted_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'proc/self').mkdir(parents=True)
            (root / 'proc/self/status').write_text(
                'CapEff:\t0000000000000000\nNoNewPrivs:\t1\nSeccomp:\t2\n')
            (root / 'proc/self/cgroup').write_text('0::/\n')
            (root / 'cgroup/cgroup.controllers').parent.mkdir(parents=True)
            (root / 'cgroup/cgroup.controllers').write_text('cpu memory pids')
            for n, x in {'memory.max': '268435456',
                         'memory.swap.max': '0', 'pids.max': '64',
                         'cpu.max': '100000 100000'}.items():
                (root / 'cgroup' / n).write_text(x)
            with patch('bountyforge.private_host_probe.platform.system', return_value='Linux'):
                with patch('bountyforge.private_host_probe.platform.machine', return_value='x86_64'):
                    with patch('bountyforge.private_host_probe.os.geteuid', return_value=1000):
                        with patch('bountyforge.private_host_probe.shutil.which',
                                   return_value='/usr/bin/unshare'):
                            with patch('bountyforge.private_host_probe.subprocess.run') as runner:
                                runner.return_value.returncode = 0
                                facts = collect_host_facts(
                                    proc_root=root / 'proc',
                                    cgroup_root=root / 'cgroup',
                                    namespace_probe=True)
            args = runner.call_args.args[0]
            self.assertEqual(args, ['/usr/bin/unshare', '-Urnmpf',
                                    '--kill-child', '/usr/bin/true'])
            self.assertTrue(facts['owned_namespace_probe_passed'])
            self.assertFalse(assess_host_facts(facts)['private_execution_admitted'])



    def test_root_cgroup_is_not_a_missing_path(self):
        from bountyforge.private_host_probe import _cgroup_relative_path
        self.assertEqual(_cgroup_relative_path('0::/\n'), [])
        self.assertEqual(_cgroup_relative_path('0::/one/two\n'), ['one', 'two'])
        for sample in ('0::/../escape\n', '0::/one//two\n',
                       '0::/one/./two\n', '1::/wrong\n',
                       '0::/one\\two\n', '0::/one\ntwo\n'):
            with self.subTest(value=sample):
                self.assertIsNone(_cgroup_relative_path(sample))
        self.assertIsNone(_cgroup_relative_path(None))


if __name__ == '__main__':
    unittest.main()
