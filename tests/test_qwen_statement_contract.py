import json
import re
import unittest
from unittest.mock import patch
from bountyforge.qwen_statement_contract import StatementModel, statement_schema
from bountyforge.statements import statement_catalog


class StatementGenerationTests(unittest.TestCase):
    def test_schema_binds_anchor_and_assignment_not_an_entire_function(self):
        source='def choose(value, fallback):\n    selected = value or fallback\n    return selected\n'
        units=list(statement_catalog(source,[2,3]).values())
        schema=statement_schema(source,units)
        changes=schema['properties']['changes']
        self.assertEqual(changes['maxItems'],3)
        assignment,returned=changes['items']['anyOf']
        self.assertEqual(assignment['properties']['line']['const'],2)
        pattern=assignment['properties']['new']['pattern']
        self.assertTrue(re.fullmatch(pattern,'selected = value if value is not None else fallback'))
        for invalid in ('def choose(value, fallback):\n    return value','other = value',
                        'selected = value\n    return selected','return value'):
            self.assertIsNone(re.fullmatch(pattern,invalid))
        self.assertTrue(re.fullmatch(returned['properties']['new']['pattern'],'return selected'))

    def test_loopback_transport_receives_bounded_schema_without_extra_calls(self):
        task={'source':'def size(xs):\n    return len(xs) - 1\n',
              'edit_units':[{'line':2,'kind':'statement','bindings':[]}], 'editable_lines':[2]}
        model=StatementModel()
        with patch.object(model,'_complete_bounded_schema',return_value='{}') as call:
            model.complete_line('trusted contract',json.dumps(task),max_tokens=150)
        call.assert_called_once()
        self.assertIn('Never output the whole function',call.call_args.args[0])
        self.assertEqual(call.call_args.args[-1],'qwen_statement_schema_v2')
        self.assertEqual(call.call_args.args[2],150)

    def test_missing_scope_cannot_become_unconstrained_generation(self):
        with self.assertRaises(ValueError):statement_schema('pass',[])
        with self.assertRaises(ValueError):StatementModel().complete_line('system','x'*3601)

