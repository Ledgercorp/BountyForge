"""Native carrier metadata and immutable-cache contracts, no inference."""
import tempfile
from pathlib import Path
import os
import unittest
from unittest.mock import patch
import phase17_sdk_bootstrap as sdk


class NativeBindingTests(unittest.TestCase):
    def test_known_package_identity_survives_secret_redaction_as_allowlisted_metadata(self):
        package='node-addon-require-builtin-linux-x64-gnu'
        record=sdk.sanitized_boot_diagnostic(('No usable native binding found for '+package+' (auto) token='+'x'*80).encode())
        self.assertEqual(record['native_package_ids'],[package])
        self.assertNotIn('x'*80,str(record));self.assertFalse(record['raw_stderr_disclosed'])
        self.assertNotIn('OPAQUE_NATIVE_PRODUCT',record['signature'])

    def test_unlisted_identifiers_are_not_published(self):
        record=sdk.sanitized_boot_diagnostic(b'No usable native binding found for private-secret-package-name-abcdefghijklmnopqrstuvwxyz (auto)')
        self.assertEqual(record['native_package_ids'],[])
        self.assertNotIn('private-secret-package-name',str(record))

    def test_readonly_cache_requires_exact_regular_binding_bytes(self):
        from phase19_native_binding import cache_admitted,CACHE_RELATIVE
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/CACHE_RELATIVE;p.parent.mkdir(parents=True)
            p.write_bytes(b'wrong');p.chmod(0o444)
            self.assertFalse(cache_admitted(root))
            p.unlink();p.symlink_to('/etc/passwd');self.assertFalse(cache_admitted(root))

    def test_wrong_carrier_never_produces_a_binding_cache(self):
        from phase19_native_binding import stage_native_cache
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/sdk.RUNTIME_BIN;p.parent.mkdir(parents=True);p.write_bytes(b'not pinned')
            with self.assertRaisesRegex(RuntimeError,'CARRIER_DIGEST'):stage_native_cache(root)
            self.assertFalse((root/'native-cache').exists())

    def test_packaged_cache_is_required_before_any_sdk_launch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/sdk.RUNTIME_BIN;p.parent.mkdir(parents=True);p.write_bytes(b'dummy')
            with self.assertRaisesRegex(RuntimeError,'IMMUTABLE_NATIVE_CACHE'):
                sdk.sdk_bootstrap_command('/usr/bin/docker',root,'bf-p17-'+'0'*16,root)

    def test_runtime_audit_cannot_accept_a_config_only_or_missing_refusal(self):
        from phase19_sdk_acceptance import validate_audit,FORBIDDEN
        record={'kind':'BOUNTYFORGE_LIVE_SDK_CAPABILITY_AUDIT','model_requests':0,
            'mcp_resources_service_present':False,'tool_names':[],
            'refusals':[{'tool':n,'available':False,'invoked':True,'unknown_tool':True} for n in FORBIDDEN]}
        validate_audit(record)
        for key,value in [('model_requests',1),('tool_names',['bash']),('mcp_resources_service_present',True),('refusals',[])]:
            with self.subTest(key=key),self.assertRaisesRegex(RuntimeError,'SDK_LIVE'):
                validate_audit({**record,key:value})

    def test_daemon_failure_is_not_proof_of_cleanup(self):
        from phase19_sdk_acceptance import remove_container
        from unittest.mock import Mock
        with patch('phase19_sdk_acceptance.subprocess.run',return_value=Mock(returncode=1,stdout=b'')):
            with self.assertRaisesRegex(RuntimeError,'CLEANUP_UNCONFIRMED'):
                remove_container('/usr/bin/docker','bf-p17-'+'0'*16)
