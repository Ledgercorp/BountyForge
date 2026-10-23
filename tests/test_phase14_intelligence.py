"""Neutral contract tests; fake observations never count as repair evidence."""
import json
import unittest
from unittest.mock import patch


class IntelligenceTests(unittest.TestCase):
    def test_failure_feedback_excludes_tracebacks_and_test_source(self):
        from bountyforge.repair_intelligence import failure_feedback
        output=('FAIL: test_total (test_regression.Contract.test_total)\n'
                'Traceback (most recent call last):\n  File "/private/tests.py", line 9\n'
                '    self.assertEqual(secret_reference(), expected)\n'
                'AssertionError: 12 != 8\nRan 7 tests\nFAILED (failures=1)')
        value=failure_feedback(output)
        self.assertEqual(value['failing_tests'],['test_total'])
        self.assertEqual(value['assertions'],['AssertionError: 12 != 8'])
        self.assertNotIn('/private',json.dumps(value));self.assertNotIn('secret_reference',json.dumps(value))

    def test_context_preserves_helpers_and_original_scope(self):
        from bountyforge.repair_intelligence import source_context
        source='def helper(x):\n    return x * 2\n\ndef total(xs):\n    return sum(helper(x) for x in xs) - 1\n'
        context=source_context(source,'total',[5])
        self.assertEqual(context['called_helpers'],['helper'])
        self.assertEqual(context['authorized_anchors'],[5])

    def test_valid_sibling_edits_are_retained_but_rejected_candidates_are_not(self):
        from bountyforge.repair_intelligence import revision_proposal
        prior={'outcome':'TEST_FAILED','candidate_sha256':'a'*64,
               'proposal':{'changes':[{'line':4,'new':'denominator = 123'}]}}
        raw=json.dumps({'changes':[{'line':7,'new':'return numerator / (denominator or 1)'}]})
        merged,retained=revision_proposal(prior,raw)
        self.assertEqual(retained,[4]);self.assertEqual(len(json.loads(merged)['changes']),2)
        value,_=revision_proposal(dict(prior,outcome='SOURCE_REJECTED'),raw)
        self.assertEqual(value,raw)

    def test_same_anchor_is_revised_and_union_does_not_exceed_three_edits(self):
        from bountyforge.repair_intelligence import revision_proposal
        prior={'outcome':'TEST_FAILED','candidate_sha256':'a'*64,
               'proposal':{'changes':[{'line':i,'new':'return 1'} for i in (1,2,3)]}}
        raw=json.dumps({'changes':[{'line':2,'new':'return 2'}]})
        merged,anchors=revision_proposal(prior,raw)
        self.assertEqual(anchors,[1,3]);self.assertEqual(json.loads(merged)['changes'][1]['new'],'return 2')
        overflow=json.dumps({'changes':[{'line':4,'new':'return 4'}]})
        value,anchors=revision_proposal(prior,overflow)
        self.assertEqual(value,overflow);self.assertEqual(anchors,[])

    def test_real_service_revalidates_retained_edits_and_reports_both_generations(self):
        from tests.test_repair_engines import EngineContractTests
        from bountyforge import repair_engines as api
        helper=EngineContractTests();helper.setUp();service=helper.service([False,True,True])
        task=service.prepare('weighted-mix','QWEN_LOCAL')
        responses=iter([{'changes':[{'line':4,'new':'denominator = 123'}]},
                        {'changes':[{'line':7,'new':'return numerator / (denominator or 1)'}]}])
        class Model:
            last_call={'prompt_tokens':1,'completion_tokens':1,'finish_reason':'stop'}
            def complete_line(self,system,user,**kwargs):
                self.prompt=json.loads(user)
                return json.dumps(next(responses))
        model=Model()
        with patch.object(api,'qwen_availability',return_value=True),patch.object(api,'LocalModel',return_value=model):
            result=service.run_qwen(task['task_id'],0)
        self.assertEqual(result['model_calls'],2)
        self.assertEqual(result['calls'][1]['retained_anchors'],[4])
        self.assertEqual(len(json.loads(result['verification_receipt']['proposal'])['changes']),2)
        self.assertEqual(model.prompt['revision_strategy'],'RETAIN_VALID_SIBLINGS_FIX_REMAINING_FAILURES')
        self.assertTrue(result['independently_verified'])  # Fake observations, NOT accuracy evidence.

    def test_multiline_generation_remains_bounded_and_does_not_authorize_declarations(self):
        from bountyforge.qwen_statement_contract import AdaptiveStatementModel
        import re
        model=AdaptiveStatementModel();source='def total(xs):\n    return sum(xs) - 1\n'
        prompt=json.dumps({'source':source,'edit_units':[{'line':2,'kind':'statement','bindings':[]}]})
        with patch.object(model,'_complete_bounded_schema',return_value='{}') as call:
            model.complete_line('contract',prompt)
        schema=call.call_args.args[3]
        pattern=schema['properties']['changes']['items']['anyOf'][0]['properties']['new']['pattern']
        self.assertIsNotNone(re.fullmatch(pattern,'return (\n    sum(xs)\n)'))
        self.assertIsNone(re.fullmatch(pattern,'def total(xs):\n    return sum(xs)'))
        self.assertIsNone(re.fullmatch(pattern,'return (\n  sum(xs)\n  + 1\n)'))

    def test_read_only_helper_context_does_not_expand_edit_authority(self):
        from tests.test_repair_engines import EngineContractTests
        helper=EngineContractTests();helper.setUp();service=helper.service()
        baseline={'passed':False,'exit_code':1,'timeout':False,
                  'output':'FAIL: test_discount_tax (test_regression.Contract.test_discount_tax)\nAssertionError\nRan 8 tests\nFAILED (failures=1)'}
        with patch.object(service.verifier,'observe',return_value=baseline):
            task=service.prepare('invoice-summary','CODEX_AGENT')
        result=service.submit(task['task_id'],0,{'changes':[{'line':2,'new':'return 0'}]})
        self.assertEqual(result['outcome'],'SOURCE_REJECTED')
        self.assertNotIn('targeted',result)

    def test_new_reads_of_later_bound_locals_are_rejected_without_relaxing_old_validator(self):
        from bountyforge.repair_intelligence import validate_local_dependencies
        from bountyforge.drafts import DraftRejected
        source='def adapt(response):\n    if response is None:\n        return []\n    rows = response\n    return rows\n'
        with self.assertRaises(DraftRejected):
            validate_local_dependencies(source,{'changes':[{'line':3,'new':'return rows'}]})
        validate_local_dependencies(source,{'changes':[{'line':5,'new':'return list(rows)'}]})

    def test_comprehension_local_bindings_are_not_confused_with_later_variables(self):
        from bountyforge.repair_intelligence import validate_local_dependencies
        source='def total(pairs):\n    result = len(pairs)\n    return result\n'
        validate_local_dependencies(source,{'changes':[{'line':2,'new':'result = sum(weight for value, weight in pairs)'}]})

    def test_dataflow_prioritization_keeps_scope_and_puts_return_dependencies_before_guards(self):
        from bountyforge.repair_intelligence import source_context
        source='def total(xs):\n    if not xs:\n        return 0\n    count = len(xs)\n    value = sum(xs)\n    return value / count\n'
        value=source_context(source,'total',[2,3,4,5,6])
        self.assertEqual(value['prioritized_anchors'][:2],[5,4])
        self.assertEqual(set(value['prioritized_anchors']),{2,3,4,5,6})
