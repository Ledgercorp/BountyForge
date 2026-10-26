import tempfile
import unittest
from pathlib import Path


class ActivationTests(unittest.TestCase):
    def test_no_approval_blocks_before_credential_or_network_access(self):
        import phase22_run as m
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'PRIVATE_AUTHORIZATION_REQUIRED'):
                m.run_experiment('a'*64,Path(t)/'missing',9999,Path(t)/'results')

    def test_frozen_plan_requires_exact_pin_and_refuses_stale_prices(self):
        import phase22_run as m
        with self.assertRaises(ValueError):m.load_plan('0'*64)
        with self.assertRaisesRegex(ValueError,'PRICING_REVALIDATION_REQUIRED'):
            m.validate_price_freshness({'prices_checked_unix':1},now=100000)

    def test_private_grant_file_and_credential_pipe_are_mandatory(self):
        import phase22_run as m
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'grant';p.write_text('{}');p.chmod(0o644)
            with self.assertRaisesRegex(ValueError,'PRIVATE_AUTHORIZATION_REQUIRED'):m.read_grant(p)
            with self.assertRaises(ValueError):m.read_client(0)
