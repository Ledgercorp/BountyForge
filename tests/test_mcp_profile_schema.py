import unittest
from bountyforge.mcp_server import _schema_args


class OptionalProfileSchemaTests(unittest.TestCase):
    def test_optional_published_profile_and_legacy_arguments_are_accepted(self):
        base={'case_id':'weighted-window','engine':'QWEN_LOCAL'}
        self.assertEqual(_schema_args('prepare_owned_repair',base),base)
        selected={**base,'model_profile':'QWEN_7B'}
        self.assertEqual(_schema_args('prepare_owned_repair',selected),selected)

    def test_unknown_keys_missing_required_and_invalid_profiles_stay_rejected(self):
        for args in [{'case_id':'weighted-window'},
                     {'case_id':'weighted-window','engine':'QWEN_LOCAL','model_profile':'PAID'},
                     {'case_id':'weighted-window','engine':'QWEN_LOCAL','execute_customer':True}]:
            with self.subTest(args=args),self.assertRaises(ValueError):_schema_args('prepare_owned_repair',args)
