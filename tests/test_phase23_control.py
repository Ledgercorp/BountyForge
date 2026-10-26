import hashlib
import json
import unittest


class EvaluationControlTests(unittest.TestCase):
    def module(self):
        try:from bountyforge import evaluation_control as m
        except ImportError:self.fail('Historical evaluation projection and execution gates are missing')
        return m

    def test_solutions_and_private_tests_are_not_persisted_by_metadata_projection(self):
        m=self.module();row={'instance_id':'org__repo-1','repo':'org/repo','base_commit':'a'*40,
            'environment_setup_commit':'b'*40,'problem_statement':'Wrong boundary result.',
            'FAIL_TO_PASS':'["tests/test_x.py::test_boundary"]','PASS_TO_PASS':'["tests/test_x.py::test_valid"]',
            'patch':'SECRET_REFERENCE','test_patch':'SECRET_TEST','hints_text':'SECRET_HINT'}
        r=m.metadata_projection(row)
        self.assertNotIn('SECRET',json.dumps(r));self.assertNotIn('problem_statement',r)
        self.assertEqual(r['expected_failing_tests'],['tests/test_x.py::test_boundary'])
        self.assertFalse(r['execution_admitted']);self.assertFalse(r['independently_unseen'])

    def test_missing_regressions_and_duplicate_test_identities_fail_closed(self):
        m=self.module()
        row={'instance_id':'x','repo':'o/r','base_commit':'a'*40,'problem_statement':'x',
             'FAIL_TO_PASS':'["t"]','PASS_TO_PASS':'[]'}
        with self.assertRaises(ValueError):m.metadata_projection(row)
        row['PASS_TO_PASS']='["t"]'
        with self.assertRaises(ValueError):m.metadata_projection(row)

    def test_reference_fields_cannot_enter_the_repair_agent_packet(self):
        m=self.module();source='def f(x):\n    return x\n'
        value={'description':'Preserve valid behavior','source':source,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
               'approved_file':'subject.py','editable_lines':[2]}
        first=m.agent_packet(value,{'stage':'TEST_FAILED','assertions':['expected 1']})
        second=m.agent_packet(value,{'stage':'SOURCE_REJECTED','assertions':['syntax']})
        self.assertEqual(first['stable_prefix_sha256'],second['stable_prefix_sha256'])
        for field in ('test_patch','reference','hidden_tests','FAIL_TO_PASS'):
            with self.assertRaises(ValueError):m.agent_packet({**value,field:'forbidden'},None)

    def test_unknown_timeout_never_becomes_a_free_retry_or_execution_admission(self):
        m=self.module()
        self.assertEqual(m.retry_policy('API_TIMEOUT',1),'STOP_UNCERTAIN_SPEND')
        self.assertEqual(m.retry_policy('TEST_FAILED',1),'REVISE_WITH_SANITIZED_FEEDBACK')
        self.assertEqual(m.retry_policy('TEST_FAILED',2),'STOP_ATTEMPT_LIMIT')
        with self.assertRaises(ValueError):m.admit_historical_execution({'hostile_code_safe':True,'owner_approved':True})
