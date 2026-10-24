"""Owned external-control client; no SDK and no model substitution.

Runs only inside the same private model sidecar. Never executes an answer.
"""
import http.client
import json
import sys


def parse_stream(raw):
    if len(raw)>65536:raise ValueError('MODEL_STREAM_BUDGET')
    content=[];done=False;usage=None
    for line in raw.splitlines():
        if not line.startswith(b'data: '):continue
        value=line[6:].strip()
        if value==b'[DONE]':done=True;break
        row=json.loads(value)
        if row.get('usage'):usage=row['usage']
        for choice in row.get('choices',[]):
            delta=choice.get('delta',{})
            if delta.get('tool_calls'):raise ValueError('MODEL_TOOL_CALL_REJECTED')
            if delta.get('content'):content.append(delta['content'])
    if not done:raise ValueError('INCOMPLETE_MODEL_STREAM')
    return {'response':''.join(content),'usage':usage}


def main():
    raw=sys.stdin.buffer.read(8193)
    if len(raw)>8192:raise ValueError('CONTROL_PROMPT_BUDGET')
    messages=json.loads(raw)
    body={'model':'bountyforge-qwen-1.5b','messages':messages,'stream':True,'max_tokens':150,'temperature':0}
    connection=http.client.HTTPConnection('127.0.0.1',8081,timeout=50)
    try:
        connection.request('POST','/v1/chat/completions',json.dumps(body),
            {'Content-Type':'application/json','Authorization':'Bearer local-no-credential'})
        reply=connection.getresponse();result=reply.read(65537)
        if reply.status!=200:raise ValueError('CONTROL_PROVIDER_REJECTED')
        print(json.dumps(parse_stream(result)))
    finally:connection.close()


if __name__=='__main__':main()
