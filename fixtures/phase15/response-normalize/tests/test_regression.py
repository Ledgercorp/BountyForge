import copy
import unittest
from subject import normalize_response


class ResponseContract(unittest.TestCase):
    def test_partial_is_success_not_transport_retry(self):
        self.assertEqual(normalize_response(206,{'records':[{'id':' x '}],'cursor':'b'},{},'a'),
            {'ok':True,'retry':False,'delay':0,'items':['x'],'cursor':'b'})

    def test_terminal_cursor(self):
        self.assertEqual(normalize_response(200,{'records':[],'cursor':None},{},'a'),
            {'ok':True,'retry':False,'delay':0,'items':[],'cursor':None})

    def test_missing_cursor_is_terminal(self):
        self.assertEqual(normalize_response(206,{'records':[]},{},'a'),
            {'ok':True,'retry':False,'delay':0,'items':[],'cursor':None})

    def test_empty_cursor_preserved(self):
        self.assertEqual(normalize_response(200,{'records':[],'cursor':''},{},'a')['cursor'],'')

    def test_retry_recovers_from_malformed_header(self):
        self.assertEqual(normalize_response(503,{}, {'Retry-After':'later'},'a'),
            {'ok':False,'retry':True,'delay':1,'items':[],'cursor':'a'})

    def test_rate_limit_delay(self):
        self.assertEqual(normalize_response(429,{}, {'Retry-After':'2.5'},'a')['delay'],2.5)

    def test_permanent_error(self):
        self.assertEqual(normalize_response(404,{}, {},'a'),
            {'ok':False,'retry':False,'delay':0,'items':[],'cursor':'a'})

    def test_filtering_and_input_custody(self):
        payload={'records':[{'id':' x '},{'id':None},{'id':' '},{'id':'y'}],'cursor':'b'}
        before=copy.deepcopy(payload)
        self.assertEqual(normalize_response(200,payload,{},'a'),
            {'ok':True,'retry':False,'delay':0,'items':['x','y'],'cursor':'b'})
        self.assertEqual(payload,before)
