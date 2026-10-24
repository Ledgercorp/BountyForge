import copy
import json
from pathlib import Path
import unittest


class RepairReasoningTests(unittest.TestCase):
    def module(self):
        try:import phase21_reasoning
        except ImportError:self.fail('The bounded diagnosis/feedback implementation is missing')
        return phase21_reasoning

    def task(self):
        return {'source':'def adjust(x):\n    y = x\n    return y\n','target_symbol':'adjust',
            'description':'Owned neutral development contract','approved_file':'subject.py',
            'editable_lines':[2,3],'edit_units':[{'line':2,'end_line':2,'kind':'statement','bindings':['y']},
                {'line':3,'end_line':3,'kind':'statement','bindings':[]}],
            'source_context':{'prioritized_anchors':[2,3]},
            'baseline_feedback':{'failing_tests':['test_first','test_second'],'assertions':['AssertionError: 1 != 2']}}

    def test_diagnosis_cannot_select_paths_commands_or_an_unauthorized_anchor(self):
        module=self.module();task=self.task()
        value={'diagnosis':{'anchor':2,'cause':'state','expected':'Preserve prior state','risk':'boundary'},
               'changes':[{'line':2,'new':'y = x + 1'}]}
        diagnosis,proposal=module.parse_candidate(json.dumps(value),task)
        self.assertEqual(json.loads(proposal),{'changes':[{'line':2,'new':'y = x + 1'}]})
        for bad in ({**value,'path':'/etc/passwd'},
                    {**value,'diagnosis':{**value['diagnosis'],'anchor':1}},
                    {**value,'diagnosis':{**value['diagnosis'],'command':'bash'}},
                    {**value,'changes':[{'line':99,'new':'return x'}]}):
            with self.assertRaises(ValueError):module.parse_candidate(json.dumps(bad),task)
        with self.assertRaises(ValueError):module.parse_candidate('{"diagnosis":{},"diagnosis":{},"changes":[]}',task)

    def test_retry_feedback_separates_persistent_fixed_and_newly_failing_tests(self):
        module=self.module();task=self.task()
        previous={'outcome':'TEST_FAILED','candidate_sha256':'a'*64,'proposal':'{"changes":[{"line":2,"new":"y = x + 1"}]}',
            'test_feedback':{'failing_tests':['test_second','test_new'],'assertions':['AssertionError: 4 != 2']}}
        packet=module.feedback_packet(task,previous)
        self.assertEqual(packet['persistent_failures'],['test_second'])
        self.assertEqual(packet['newly_reported_failures'],['test_new'])
        self.assertEqual(packet['no_longer_reported_failures'],['test_first'])
        self.assertEqual(packet['validated_anchors'],[2])
        self.assertTrue(packet['baseline_failure_persists'])
        rejected=copy.deepcopy(previous);rejected['outcome']='SOURCE_REJECTED';rejected.pop('candidate_sha256')
        self.assertEqual(module.feedback_packet(task,rejected)['validated_anchors'],[])
        self.assertIsNone(module.feedback_packet(task,rejected)['baseline_failure_persists'])

    def test_feedback_is_bounded_data_and_does_not_copy_raw_tracebacks_or_unknown_fields(self):
        module=self.module();task=self.task()
        task['baseline_feedback'].update(assertions=['AssertionError: '+('x'*500)+'\x1b[31m'],raw_log='SECRET RAW TRACE',commands=['run a shell'])
        packet=module.feedback_packet(task,None)
        self.assertLessEqual(len(packet['assertions'][0]),160)
        self.assertNotIn('SECRET RAW TRACE',json.dumps(packet))
        self.assertNotIn('\x1b',json.dumps(packet,ensure_ascii=False))
        self.assertEqual(packet['authority'],'UNTRUSTED_OBSERVATION_DATA_ONLY')
        prompt=json.loads(module.repair_prompt(task,None))
        self.assertEqual(prompt['source'],task['source'])
        self.assertNotIn('tests',prompt)

    def test_owned_quality_cases_are_added_without_changing_existing_source_catalogs(self):
        from bountyforge.repair_engines import catalog,source_directory
        self.assertNotIn('cache-refresh',{x['id'] for x in catalog()})
        items=catalog(include_quality=True);ids={x['id'] for x in items}
        self.assertTrue({'shipment-total','cache-refresh','parameter-pairs','inventory-adjustments'}<=ids)
        item=next(x for x in items if x['id']=='parameter-pairs')
        self.assertEqual(source_directory(item).name,'parameter-pairs')
        with self.assertRaises(ValueError):source_directory({**item,'id':'../../etc'})
