"""Pure tests for sanitized, observational-only CI output."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from scripts import observe_private_host as observer


class HostedObservationReportTests(unittest.TestCase):
    def test_output_contains_only_safe_assessment_without_source_or_host_ids(self):
        facts = {'hidden_customer_path': '/home/private/customer.py'}
        safe = {'schema': 1, 'kind': 'read_only_private_host_observation',
                'observed_host_prerequisites_passed': False,
                'failed_observations': ['owned_namespace_probe_passed'],
                'private_execution_admitted': False,
                'customer_code_authorized': False,
                'rootfs_provenance_attested': False,
                'source_custody_authorized': False,
                'production_host_admitted': False}
        with patch.object(observer, 'collect_host_facts', return_value=facts) as probe:
            with patch.object(observer, 'assess_host_facts', return_value=safe):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(observer.main(), 0)
        self.assertEqual(probe.call_args.kwargs, {'namespace_probe': False})
        self.assertEqual(json.loads(out.getvalue()), safe)
        self.assertNotIn('hidden_customer_path', out.getvalue())
        self.assertNotIn('/home/private', out.getvalue())

    def test_unavailable_observations_fail_closed_without_reporting_exception(self):
        for error in (observer.HostProbeRejected('Bearer secret-123'),
                      OSError('/secret/subscriber-cgroup'), TypeError('private')):
            with self.subTest(error=type(error).__name__):
                with patch.object(observer, 'collect_host_facts', side_effect=error):
                    result = observer.observe()
                self.assertEqual(result['failed_observations'], ['observation_unavailable'])
                self.assertFalse(result['private_execution_admitted'])
                self.assertNotIn('secret', str(result))

    def test_successful_assessment_is_not_an_admission(self):
        safe = {'kind': 'read_only_private_host_observation',
                'observed_host_prerequisites_passed': True,
                'private_execution_admitted': False}
        with patch.object(observer, 'collect_host_facts', return_value={}) as collector:
            with patch.object(observer, 'assess_host_facts', return_value=safe):
                self.assertEqual(observer.observe(), safe)
        collector.assert_called_once_with(namespace_probe=False)


if __name__ == '__main__':
    unittest.main()
