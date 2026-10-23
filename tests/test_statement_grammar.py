import re
import unittest
from bountyforge.qwen_statement_contract import statement_schema
from bountyforge.statement_grammar import statement_grammar


class StatementGrammarTests(unittest.TestCase):
    def schema(self):
        return statement_schema('def owned(value):\n    total = value\n    return total\n',
                                [{'line':2,'kind':'statement'},{'line':3,'kind':'statement'}])

    def test_reproduces_raw_pattern_delimiter_escape_and_grammar_excludes_it(self):
        schema=self.schema();pattern=schema['properties']['changes']['items']['anyOf'][1]['properties']['new']['pattern']
        witness='return value"},{"line":3,"new":"return value'
        self.assertIsNotNone(re.fullmatch(pattern,witness))
        grammar=statement_grammar(schema)
        self.assertIn(r'atom ::= [^"\\\x00-\x1f]',grammar)
        self.assertIn('(ws "," ws edit){0,2}',grammar)
        self.assertIn('"\\\"total = "',grammar);self.assertIn('"\\\"return "',grammar)
        self.assertNotIn('"99"',grammar)

    def test_untrusted_anchor_prefix_and_expanded_budget_are_rejected(self):
        for mutation in ('anchor','prefix','budget'):
            schema=self.schema();changes=schema['properties']['changes']
            item=changes['items']['anyOf'][0]
            if mutation=='anchor':item['properties']['line']['const']=True
            if mutation=='prefix':item['properties']['new']['pattern']='^arbitrary() [^\\r\\n]+$'
            if mutation=='budget':changes['maxItems']=4
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):statement_grammar(schema)

    def test_compact_wire_changes_only_json_whitespace_not_scope_or_code_strings(self):
        original=statement_grammar(self.schema());compact=statement_grammar(self.schema(),compact=True)
        self.assertEqual(original.replace('ws ::= [ \\t\\n\\r]{0,8}','ws ::= ""'),compact)
        self.assertIn('atom{1,160}',compact);self.assertIn('continuation{0,2}',compact)

    def test_condition_units_have_expression_delimiters_without_changing_other_statements(self):
        schema=self.schema();entry=schema['properties']['changes']['items']['anyOf'][0]
        entry['properties']['new']['pattern']=r'^[^\r\n]{1,400}$'
        entry['x-owned-unit-kind']='condition'
        grammar=statement_grammar(schema,compact=True)
        condition=next(r for r in grammar.splitlines() if r.startswith('edit0 ::='))
        self.assertIn('"\\\"("',condition);self.assertIn('")\\\""',condition)
        returned=next(r for r in grammar.splitlines() if r.startswith('edit1 ::='))
        self.assertIn('return ',returned)
