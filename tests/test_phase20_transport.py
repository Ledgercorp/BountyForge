import tempfile
from pathlib import Path
import unittest


class NativeTransportTests(unittest.TestCase):
    def test_runtime_dependency_cannot_be_supplied_as_unverified_library_bytes(self):
        from phase20_dependency import stage_library
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);deb=p/'untrusted.deb';deb.write_bytes(b'!<arch>\nnot a signed-index-pinned package')
            with self.assertRaisesRegex(ValueError,'LIBGOMP_PACKAGE_DIGEST'):
                stage_library(deb,p/'dependencies')
            self.assertFalse((p/'dependencies').exists())

    def test_sdk_namespace_join_cannot_select_host_or_an_arbitrary_container(self):
        from phase20_transport import sdk_command
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            for namespace in ('host','bridge','container:unrelated','bf-p20-model-'+('a'*16)+',host'):
                with self.subTest(namespace=namespace),self.assertRaisesRegex(ValueError,'NAMESPACE'):
                    sdk_command('/usr/bin/docker',p,'bf-p17-'+'a'*16,p,namespace)

    def test_model_and_sdk_keep_independent_limits_and_no_host_access(self):
        from phase20_transport import model_command
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            cmd=model_command('/usr/bin/docker',p,'bf-p20-model-'+'a'*16,p)
            for value in ('--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
                          '--memory=3g','--memory-swap=3g','--cpus=2','--pids-limit=64','--user=65534:65534'):
                self.assertIn(value,cmd)
            self.assertFalse(any('docker.sock' in a or '--publish' in a or '--privileged' in a for a in cmd))
            self.assertTrue(all('readonly' in a for a in cmd if a.startswith('--mount=')))

    def test_unpinned_runtime_is_never_extracted_or_executed(self):
        from phase20_transport import stage_assets
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cache=root/'cache';(cache/'runtime').mkdir(parents=True)
            (cache/'runtime/llama-b11750-bin-ubuntu-x64.tar.gz').write_bytes(b'untrusted')
            with self.assertRaisesRegex(ValueError,'RUNTIME_DIGEST'):
                stage_assets(root/'staged',cache)
            self.assertFalse((root/'staged').exists())

    def test_runtime_controls_cannot_treat_a_missing_egress_check_as_safe(self):
        from phase20_transport import validate_model_boundary
        with self.assertRaisesRegex(ValueError,'MODEL_BOUNDARY'):
            validate_model_boundary({'network_none':True})
