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
    def test_environment_allowlist_uses_trusted_docker_path_and_drops_all_other_variables(self):
        command=[sys.executable,'-c',
            'import os,json;from bountyforge.mcp_server import _isolate_environment;'
            '_isolate_environment();print(json.dumps({"names":sorted(os.environ),"paths":os.get_exec_path()}))']
        env=dict(os.environ,UNRELATED_SECRET_TOKEN='must-never-be-inherited')
        p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,'MCP startup environment isolation is missing')
        self.assertEqual(json.loads(p.stdout),{'names':['PATH'],'paths':['/usr/local/bin','/usr/bin','/bin']})

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
            'verify_owned_reference','preview_owned_review_package','list_repair_engines',
            'list_owned_repair_tasks','prepare_owned_repair','submit_owned_repair','run_owned_qwen',
            'create_owned_queue','claim_owned_queue','submit_owned_queue','run_owned_queue_qwen',
            'heartbeat_owned_queue','release_owned_queue','owned_queue_status','stop_owned_queue'})
        original={'bountyforge_status','list_owned_calibration','inspect_owned_calibration',
                  'verify_owned_reference','preview_owned_review_package'}
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in tools if t['name'] in original))
        self.assertTrue(all(not t['annotations']['readOnlyHint'] for t in tools
                            if t['name'] in {'prepare_owned_repair','submit_owned_repair','run_owned_qwen',
            'create_owned_queue','claim_owned_queue','submit_owned_queue','run_owned_queue_qwen',
            'heartbeat_owned_queue','release_owned_queue','stop_owned_queue'}))
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

    def test_standard_request_metadata_does_not_change_authority(self):
        # Actual Codex 0.163.0 sends this progress token during discovery.
        p, records = self.interact([INIT, READY,
            request(2, 'tools/list', {'_meta': {'progressToken': 0}}),
            request(3, 'tools/call', {'name': 'bountyforge_status',
                'arguments': {}, '_meta': {'progressToken': 'status'}}),
            request(4, 'tools/call', {'name': 'bountyforge_status',
                'arguments': {'delivery_authorized': True}, '_meta': {}})])
        self.assertEqual(p.returncode, 0)
        self.assertEqual(len(records[1]['result']['tools']), 18)
        status = json.loads(records[2]['result']['content'][0]['text'])
        self.assertFalse(status['delivery_authorized'])
        self.assertTrue(records[3]['result']['isError'])

    def test_metadata_must_be_an_object_and_cannot_supply_operations(self):
        p, records = self.interact([INIT, READY,
            request(2, 'tools/list', {'_meta': 'not-an-object'}),
            request(3, 'tools/list', {'_meta': {}, 'cursor': 'unavailable'}),
            request(4, 'tools/call', {'name': 'bountyforge_status',
                'arguments': {}, '_meta': []}),
            request(5, 'tools/call', {'name': 'bountyforge_status',
                'arguments': {}, '_meta': {}, 'command': 'forbidden'})])
        self.assertEqual(p.returncode, 0)
        self.assertTrue(all(r['error']['code'] == -32602 for r in records[1:]))

    def test_new_engine_tools_are_real_bounded_interfaces_not_arbitrary_source_intake(self):
        p,records=self.interact([INIT,READY,tool(2,'list_repair_engines'),tool(3,'list_owned_repair_tasks'),
            tool(4,'prepare_owned_repair',{'case_id':'weighted-mix','engine':'PAID_API'}),
            tool(5,'prepare_owned_repair',{'case_id':'../../private','engine':'CODEX_AGENT'}),
            tool(6,'submit_owned_repair',{'task_id':'0'*32,'revision':False,'proposal':{'changes':[]}}),
            tool(7,'submit_owned_repair',{'task_id':'0'*32,'revision':0,
                 'proposal':{'changes':[{'line':4,'new':'denominator = 1','path':'secret.py'}]}}),
            tool(8,'run_owned_qwen',{'task_id':'0'*32,'revision':0})])
        self.assertEqual(p.returncode,0)
        payload=json.loads(records[1]['result']['content'][0]['text'])
        self.assertEqual([x['id'] for x in payload['engines']],['QWEN_LOCAL','CODEX_AGENT'])
        self.assertFalse(payload['engines'][1]['unattended_backend_available'])
        tasks=json.loads(records[2]['result']['content'][0]['text'])
        self.assertEqual(len(tasks['tasks']),6)
        self.assertFalse(tasks['independent_evaluation'])
        self.assertTrue(all(x['result']['isError'] for x in records[3:]))
        self.assertNotIn(b'private',p.stdout.splitlines()[-1])

    def test_queue_schemas_reject_unbounded_jobs_source_and_approval_flags(self):
        lease={'batch_id':'trial','job_id':'0'*32,'lease_token':'0'*32}
        p,records=self.interact([INIT,READY,
            tool(2,'create_owned_queue',{'batch_id':'trial','engine':'CODEX_AGENT','case_ids':['chunk-count']*6}),
            tool(3,'create_owned_queue',{'batch_id':'trial','engine':'CODEX_AGENT','case_ids':['chunk-count'],'source':'private'}),
            tool(4,'submit_owned_queue',dict(lease,revision=True,proposal={'changes':[{'line':4,'new':'return 0'}]})),
            tool(5,'stop_owned_queue',{'batch_id':'trial','resume':True}),
            tool(6,'claim_owned_queue',{'batch_id':'trial','customer_execution_authorized':True})])
        self.assertEqual(p.returncode,0)
        self.assertTrue(all(row['result']['isError'] for row in records[1:]))

if __name__=='__main__': unittest.main()
