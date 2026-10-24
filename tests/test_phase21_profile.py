import json
from pathlib import Path
import tempfile
import unittest


class OptionalContainedModelTests(unittest.TestCase):
    def test_granite_model_cgroup_is_explicit_and_rejects_unapproved_profiles(self):
        from phase20_transport import model_command
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            try:command=model_command('/usr/bin/docker',root,'bf-p20-model-'+'b'*16,root,profile='GRANITE42_3B')
            except TypeError:self.fail('Independent experimental Granite resource profile is missing')
            self.assertIn('--memory=5g',command);self.assertIn('--memory-swap=5g',command)
            self.assertIn('--network=none',command)
            with self.assertRaises(ValueError):model_command('/usr/bin/docker',root,'bf-p20-model-'+'b'*16,root,profile='unapproved')

    def test_gateway_binds_the_selected_model_and_rejects_cross_profile_or_paid_routing(self):
        from phase20_model_service import admit_request
        raw=json.dumps({'model':'bountyforge-granite-3b','messages':[{'role':'user','content':'owned'}], 'stream':True,'max_tokens':150}).encode()
        try:request=admit_request('/v1/chat/completions',raw,expected_model='bountyforge-granite-3b')
        except TypeError:self.fail('The gateway cannot bind an explicit admitted model identity')
        self.assertEqual(request['model'],'bountyforge-granite-3b')
        with self.assertRaises(ValueError):admit_request('/v1/chat/completions',raw)
        with self.assertRaises(ValueError):admit_request('/v1/chat/completions',raw,expected_model='paid-fallback')
