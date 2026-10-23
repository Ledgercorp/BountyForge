"""External MCP stdio protocol acceptance against a real separate process."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CMD = [sys.executable, '-m', 'bountyforge.mcp_server']
INIT = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{
    'protocolVersion':'2025-11-25', 'capabilities':{},
    'clientInfo':{'name':'bountyforge-blackbox','version':'1.0'}}}
READY = {'jsonrpc':'2.0','method':'notifications/initialized'}


def request(id, method, params=None):
    obj = {'jsonrpc':'2.0','id':id,'method':method}
    if params is not None:
        obj['params']=params
    return obj


def tool(id, name, arguments=None):
    return request(id,'tools/call',{'name':name,'arguments':{} if arguments is None else arguments})


class MCPBlackBoxTests(unittest.TestCase):
    def interact(self, messages):
        env=dict(os.environ)
        for key in ('GROQ_API_KEY','STRIPE_SECRET_KEY','OPENAI_API_KEY','GITHUB_TOKEN'):
            env[key]='sensitive-token-that-must-not-appear'
        env['PYTHONDONTWRITEBYTECODE']='1'
        data=b''.join((json.dumps(x).encode()+b'\n') if not isinstance(x,bytes) else x for x in messages)
        p=subprocess.run(CMD,input=data,capture_output=True,env=env,cwd=ROOT,timeout=10)
        self.assertNotIn(b'sensitive-token',p.stdout+p.stderr)
        self.assertNotIn(b'Traceback',p.stderr)
        output=[json.loads(line) for line in p.stdout.splitlines()]
        return p,output

    def test_initialize_and_tool_discovery_are_real_protocol_messages(self):
        p,records=self.interact([INIT,READY,request(2,'tools/list'),request(3,'ping')])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(records),3)
        self.assertEqual(records[0]['result']['protocolVersion'],'2025-11-25')
        self.assertEqual(records[0]['result']['serverInfo']['name'],'bountyforge-owned-review')
        tools=records[1]['result']['tools']
        self.assertEqual({t['name'] for t in tools},{
            'bountyforge_status','list_owned_calibration', 'inspect_owned_calibration',
            'verify_owned_reference','preview_owned_review_package'})
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in tools))
        self.assertTrue(all(t['inputSchema']['additionalProperties'] is False for t in tools))
        self.assertEqual(records[2]['result'],{})

    def test_all_five_owned_tools_and_publisher_status_do_not_escalate(self):
        calls=[tool(2,'bountyforge_status'),tool(3,'list_owned_calibration'),
            tool(4,'inspect_owned_calibration',{'case_id':'page-offset-boundary'}),
            tool(5,'verify_owned_reference',{'case_id':'page-offset-boundary'}),
            tool(6,'preview_owned_review_package')]
        p,records=self.interact([INIT,READY,*calls])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(records),6)
        payload=[]
        for response in records[1:]:
            self.assertFalse(response['result']['isError'],response)
            payload.append(json.loads(response['result']['content'][0]['text']))
        self.assertIs(payload[0]['private_execution_admitted'],False)
        self.assertIs(payload[0]['commercial_launch_authorized'],False)
        self.assertIs(payload[0]['runtime']['publisher_signature_verified'],False)
        self.assertIs(payload[0]['live_model_accuracy'],None)
        self.assertEqual(len(payload[1]['cases']),4)
        self.assertFalse(payload[2]['reference_solution_disclosed'])
        self.assertIn('start = number * size + 1',payload[2]['source'])
        self.assertEqual(payload[3]['authorship'],'preauthored_reference_only')
        self.assertFalse(payload[3]['ai_generated_patch'])
        self.assertTrue(payload[4]['preview_only'])
        self.assertEqual(payload[4]['files_written'],0)
        self.assertFalse(payload[4]['delivery_authorized'])

    def test_denies_fake_approval_customer_code_and_hidden_scope(self):
        p,records=self.interact([INIT,READY,
            tool(2,'bountyforge_status',{'payment_verified':True}),
            tool(3,'inspect_owned_calibration',{'case_id':'../../secret'}),
            tool(4,'verify_owned_reference',{'case_id':'page-offset-boundary','new':'import os'}),
            tool(5,'execute_customer_code',{'command':'pwd'}),
            tool(6,'preview_owned_review_package',{'output_dir':'/tmp/foo'})])
        self.assertEqual(p.returncode,0)
        self.assertTrue(records[1]['result']['isError'])
        self.assertTrue(records[2]['result']['isError'])
        self.assertTrue(records[3]['result']['isError'])
        self.assertEqual(records[4]['error']['code'],-32602)
        self.assertTrue(records[5]['result']['isError'])
        self.assertNotIn(b'../../secret',p.stdout)

    def test_handshake_invalid_method_and_version_negotiation(self):
        other=dict(INIT);other['params']=dict(INIT['params'],protocolVersion='2099-01-01')
        p,records=self.interact([request(1,'tools/list'),other,request(3,'tools/list'),READY,
                                 request(4,'tools/list'),request(5,'execute')])
        self.assertEqual(p.returncode,0)
        self.assertEqual(records[0]['error']['code'],-32000)
        self.assertEqual(records[1]['result']['protocolVersion'],'2025-11-25')
        self.assertEqual(records[2]['error']['code'],-32000)
        self.assertTrue(records[3]['result']['tools'])
        self.assertEqual(records[4]['error']['code'],-32601)

    def test_duplicate_json_keys_and_oversized_line_fail_closed(self):
        malicious=b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"ping"}\n'
        p,res=self.interact([malicious])
        self.assertEqual(p.returncode,0)
        self.assertEqual(res[0]['error']['code'],-32700)
        big=b'{"' + b'x' * 9000 + b'":"y"}\n'
        p,res=self.interact([big])
        self.assertEqual(p.returncode,2)
        self.assertEqual(res,[])

    def test_notifications_do_not_yield_stdout_and_unknown_calls_do_not_break_later_tools(self):
        p,res=self.interact([INIT,READY,
            {'jsonrpc':'2.0','method':'notifications/progress','params':{'progress':10}},
            request(2,'other/method'),tool(3,'bountyforge_status')])
        self.assertEqual(p.returncode,0)
        self.assertEqual(len(res),3)
        self.assertEqual(res[1]['error']['code'],-32601)
        self.assertFalse(res[2]['result']['isError'])

if __name__=='__main__': unittest.main()
