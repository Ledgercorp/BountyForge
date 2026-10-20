"""Offline, source-attributed, review-only 5-issue Boltons Qwen benchmark.

Only manually curated upstream excerpts are executable. No claim that this is
certified untrusted-code isolation or full upstream suite verification.
"""
from __future__ import annotations
import ast, difflib, json, os, shutil, signal, subprocess, tempfile, time, urllib.request, urllib.error, resource, sys, re
from pathlib import Path
class _NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self, req, fp, code, msg, headers, url): raise RuntimeError('Loopback inference redirect forbidden')
ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/'tasks/manifest.json').read_text())
SCHEMA={'type':'object','properties':{'edits':{'type':'array','minItems':1,'maxItems':3,'items':{'type':'object','properties':{'path':{'type':'string'},'old':{'type':'string'},'new':{'type':'string'}},'required':['path','old','new'],'additionalProperties':False}}},'required':['edits'],'additionalProperties':False}
SYSTEM=('Repair one Python bug. Output JSON only: {"edits":[{"path":"file.py","old":"exact original snippet","new":"replacement"}]}. Use the exact file path. Only 1-3 short edits; no Markdown.')

def limits():
  resource.setrlimit(resource.RLIMIT_CPU,(8,8));resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))

def tests(root, timeout=12):
  # Vetted excerpt only, Linux unprivileged network+PID namespace; host VFS is NOT chroot-isolated here.
  cmd=['unshare','-Urnmpf','--kill-child',sys.executable,'-B','-m','unittest','discover','-s','tests','-q']
  env={'PATH':'/usr/bin:/bin','HOME':str(root),'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8'}
  start=time.monotonic()
  try:
    p=subprocess.Popen(cmd,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,preexec_fn=limits)
    try: output,_=p.communicate(timeout=timeout);timedout=False
    except subprocess.TimeoutExpired:
      os.killpg(p.pid,signal.SIGKILL);output,_=p.communicate();timedout=True
    return {'passed':p.returncode==0 and not timedout and bool(re.search(rb'Ran [1-9][0-9]* tests?',output)) and output.rstrip().endswith(b'OK'),'returncode':p.returncode,'timeout':timedout,'elapsed_seconds':round(time.monotonic()-start,3),'output':output.decode('utf-8','replace')[-1300:]}
  except Exception as e:
    return {'passed':False,'error':str(e)[:130],'elapsed_seconds':round(time.monotonic()-start,3)}

def focus(task_id, source):
  lines=source.splitlines()
  if task_id=='454':
    keep=('def args2sh(', "return ' '.join(ret_list)",'def args2cmd(', 'if result:', "result.append(' ')", "return ''.join(result)")
    return '\n'.join(line for line in lines if any(k in line for k in keep))
  if task_id=='459':
    return '\n'.join(line for line in lines if any(k in line for k in ('_SIZE_SYMBOLS', '_SIZE_BOUNDS', '_SIZE_RANGES','def bytes2human(', 'abs_bytes =', 'for (size', 'if abs_bytes', 'hnbytes =','return ')))
  if task_id=='475':
    return '\n'.join(line for line in lines if any(k in line for k in ('_line_ending_re', 'def iter_splitlines(', 'for match', 'yield ')))
  if task_id=='460':
    return source[source.index('    def most_common('):]
  if task_id=='524':
    return '\n'.join(line for line in lines if any(k in line for k in ('_SIZE_SYMBOLS', '_SIZE_BOUNDS', '_SIZE_RANGES','def bytes2human(', 'abs_bytes =', 'for (size', 'if abs_bytes', 'hnbytes =','return ')))
  return source[:1300]

def propose(issue, source, filename, feedback):
  prompt=json.dumps({'file':filename,'symptom':issue['description'][:280], 'source_excerpt':focus(issue['id'],source)[:1150],'last_failure':feedback[:120]},ensure_ascii=False)
  data=json.dumps({'model':'local','messages':[{'role':'system','content':SYSTEM+' Exact path: '+filename},{'role':'user','content':prompt}], 'max_tokens':115,'temperature':0,'stream':False,'response_format':{'type':'json_schema','json_schema':{'name':'minimal_edit','strict':True,'schema':SCHEMA}}}).encode()
  req=urllib.request.Request('http://127.0.0.1:18080/v1/chat/completions',data=data,headers={'Content-Type':'application/json'},method='POST')
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())
  start=time.monotonic()
  with opener.open(req,timeout=65) as rsp: info=json.loads(rsp.read())
  return info['choices'][0]['message']['content'],info.get('usage',{}),round(time.monotonic()-start,2)

def stage(source, raw,filename):
  if len(raw.encode())>12000:raise ValueError('response_over_limit')
  data=json.loads(raw)
  if set(data)!={'edits'} or not isinstance(data['edits'],list) or not 1<=len(data['edits'])<=3:raise ValueError('invalid_schema')
  updated=source
  for e in data['edits']:
    if not isinstance(e,dict) or set(e)!={'path','old','new'}:raise ValueError('invalid_edit_schema')
    if e['path']!=filename:raise ValueError('unauthorized_path')
    old,new=e['old'],e['new']
    if not isinstance(old,str) or not isinstance(new,str) or not old or old==new or len(old)>700 or len(new)>1000:raise ValueError('invalid_change')
    if updated.count(old)!=1:raise ValueError('not_unique_or_missing')
    updated=updated.replace(old,new,1)
  ast.parse(updated,filename=filename)
  diff=''.join(difflib.unified_diff(source.splitlines(True),updated.splitlines(True),fromfile='a/'+filename,tofile='b/'+filename))
  if not diff:raise ValueError('no_effect')
  return updated,diff

def run():
  report={'benchmark':'boltons_26.1.0_curated_excerpts','run_type':'real_qwen_cpu','historical_source_tag':'26.1.0',
     'verification_scope':'excerpt_only_no_full_upstream_suite','isolation':'network_PID_user_mount_namespaces_rlimits; host FS NOT chroot isolated; only vetted extracts',
     'external_submission':False,'paid_inference':False,'tasks':[]}
  for task in MANIFEST['tasks']:
    start=time.monotonic()
    item={k:task[k] for k in ['id','issue','blob']}; item.update({'status':'failed','model_calls':0,'model_generated_success':False,'attempts':[]})
    source_dir=ROOT/'tasks'/task['id']; original=(source_dir/task['file']).read_text()
    with tempfile.TemporaryDirectory(prefix='bf-historical-') as wd:
      wd=Path(wd); shutil.copytree(source_dir,wd/'base');base=wd/'base'
      baseline=tests(base);item['baseline']=baseline
      if baseline['passed'] or baseline.get('timeout') or baseline.get('returncode') != 1 or 'FAILED (failures=' not in baseline.get('output',''):
        item['failure_reason']='baseline_not_reproduced_or_runner_unavailable'
      else:
        previous=baseline['output'][-300:]
        for i in range(1,3):
          work=wd/f'attempt{i}';shutil.copytree(base,work)
          one={'number':i,'status':'failed'};item['model_calls']+=1
          try:
            raw,usage,seconds=propose(task,original,task['file'],previous)
            one.update({'generation_seconds':seconds,'tokens':usage})
            edited,diff=stage(original,raw,task['file'])
            (work/task['file']).write_text(edited)
            check=tests(work);one['test']=check
            if check['passed']:
              one.update({'status':'passed','diff':diff[:2500]});item['status']='review_ready';item['model_generated_success']=True;item['patch']=diff[:3000];item['attempts'].append(one);break
            one['failure_reason']='targeted_tests_failed';previous=check['output'][-300:]
          except (ValueError,SyntaxError,KeyError,TypeError) as e:
            one['failure_reason']=type(e).__name__;one['message']=str(e)[:150];previous='The previous patch was rejected: '+one['message']
          except (RuntimeError,TimeoutError,urllib.error.URLError) as e:
            one['failure_reason']='inference_unavailable_or_timeout';one['message']=type(e).__name__
            item['attempts'].append(one);break # cannot safely retry hung endpoint
          item['attempts'].append(one)
    item['elapsed_seconds']=round(time.monotonic()-start,2)
    report['tasks'].append(item)
    report['completed']=len(report['tasks']);report['attempted']=sum(1 for x in report['tasks'] if x['model_calls'])
    report['passed']=sum(x['model_generated_success'] for x in report['tasks'])
    (ROOT.parents[1]/'evidence/phase4_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('case',task['id'],item['status'],'calls',item['model_calls'],'seconds',item['elapsed_seconds'],flush=True)
  return report
if __name__=='__main__':
 res=run();print('SUMMARY',res['passed'],'/',res['attempted'])