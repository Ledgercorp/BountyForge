from pathlib import Path
import tempfile
import unittest


class EffectiveCapacityTests(unittest.TestCase):
    def observe(self,group,proc):
        from phase21_runner import observe_capacity
        return observe_capacity(group,proc,affinity_cpus=4)

    def prepare(self,root):
        group=root/'group';proc=root/'proc';group.mkdir();(proc/'self').mkdir(parents=True)
        (group/'cgroup.controllers').write_text('cpu memory pids\n')
        (proc/'self/cgroup').write_text('0::/worker\n');(group/'worker').mkdir()
        (proc/'meminfo').write_text('MemAvailable: 12582912 kB\n')
        return group,proc

    def test_real_process_path_and_ancestor_limits_outrank_unlimited_leaf(self):
        with tempfile.TemporaryDirectory() as temp:
            group,proc=self.prepare(Path(temp));leaf=group/'worker'
            (leaf/'memory.max').write_text('max');(leaf/'memory.current').write_text('0')
            (leaf/'cpu.max').write_text('max 100000')
            (group/'memory.max').write_text(str(8*1024**3));(group/'memory.current').write_text(str(5*1024**3))
            (group/'cpu.max').write_text('100000 100000')
            try:r=self.observe(group,proc)
            except ImportError:self.fail('Effective cgroup capacity observation is missing')
            self.assertEqual(r['available_memory_bytes'],3*1024**3)
            self.assertEqual(r['available_cpu_count'],1)

    def test_kernel_root_without_max_files_uses_verified_v2_identity_and_host_availability(self):
        with tempfile.TemporaryDirectory() as temp:
            group,proc=self.prepare(Path(temp));(proc/'self/cgroup').write_text('0::/\n')
            try:r=self.observe(group,proc)
            except ImportError:self.fail('Root cgroup capacity observation is missing')
            self.assertEqual(r['available_memory_bytes'],12*1024**3)
            self.assertEqual(r['available_cpu_count'],4)
            self.assertEqual(r['process_cgroup'],'/')
            (proc/'self/cgroup').write_text('0::/missing\n')
            with self.assertRaises(ValueError):self.observe(group,proc)
            (proc/'self/cgroup').write_text('0::/../../outside\n')
            with self.assertRaises(ValueError):self.observe(group,proc)

    def test_unrecognized_controller_layout_never_becomes_unlimited(self):
        with tempfile.TemporaryDirectory() as temp:
            group,proc=self.prepare(Path(temp));(group/'cgroup.controllers').unlink()
            with self.assertRaises((ValueError,OSError)):self.observe(group,proc)
