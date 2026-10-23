import json
import unittest
from bountyforge import repair_intelligence as intelligence


class CompactContextTests(unittest.TestCase):
    def public(self):
        return {'approved_file':'subject.py','source':'def select(values):\n    result = values[0]\n    return result\n',
            'target_symbol':'select','description':'Choose the supported value without mutating input.',
            'editable_lines':[2,3],'edit_units':[{'line':2,'end_line':2,'kind':'statement','bindings':['result']},
                                            {'line':3,'end_line':3,'kind':'statement','bindings':[]}],
            'proposal_protocol':'ast_statement_v1',
            'source_context':{'target_range':[1,3],'called_helpers':[],'authorized_anchors':[2,3],
                              'prioritized_anchors':[2,3],'scope_policy':'Helpers are read only'},
            'baseline_feedback':{'failing_tests':['test_selection'],'assertions':['AssertionError: actual != expected'],
                                 'classification':'OWNED_DEVELOPMENT_FEEDBACK','unseen_evaluation':False}}

    def test_compaction_preserves_source_problem_actual_feedback_and_all_units(self):
        public=self.public();raw=intelligence.compact_model_prompt(public,None);task=json.loads(raw)
        self.assertEqual(task['source'],public['source']);self.assertEqual(task['description'],public['description'])
        self.assertEqual(task['failure_feedback'],public['baseline_feedback'])
        self.assertEqual([u['line'] for u in task['edit_units']],public['editable_lines'])
        self.assertLess(len(raw),len(intelligence.model_prompt(public,None)))
        self.assertNotIn('source_context',task);self.assertNotIn('editable_lines',task)

    def test_retry_keeps_exact_prior_proposal_and_diagnostic(self):
        previous={'outcome':'SOURCE_REJECTED','proposal':'{invalid}','diagnostic':'Invalid structured JSON proposal'}
        task=json.loads(intelligence.compact_model_prompt(self.public(),previous))
        self.assertEqual(task['previous_proposal'],previous['proposal'])
        self.assertEqual(task['previous_error'],previous['diagnostic'])
