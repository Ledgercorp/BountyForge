"""Explicit trusted owner CLI. CI and preparation cannot spend provider credits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import time
from bountyforge.repair_engines import strict_json,receipt_hash
from phase22_budget import Budget,private,validate_grant,microusd
from phase22_deepseek import DeepSeekClient,admitted_models,usd_balance

ROOT=Path(__file__).resolve().parent
STORE=ROOT/'.bountyforge-phase22'


def write_receipt(path,record):
    record['receipt_sha256']=receipt_hash(record)
    raw=json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+'\n'
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # Exact caller-selected output, never a provider-selected path. Atomic,
    # bounded records; do not follow output symlinks or overwrite unrelated files.
    if path.is_symlink():raise ValueError('OUTPUT_SYMLINK_REJECTED')
    temp=path.with_name(path.name+'.pending')
    fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()


def read_grant(path):
    path=Path(path)
    try:
        private(path)
        if path.stat().st_size>4096:raise ValueError('PRIVATE_AUTHORIZATION_REQUIRED')
        return strict_json(path.read_bytes())
    except (OSError,ValueError):raise ValueError('PRIVATE_AUTHORIZATION_REQUIRED') from None


def read_client(fd):
    if type(fd) is not int or fd<3 or not stat.S_ISFIFO(os.fstat(fd).st_mode):
        raise ValueError('TRUSTED_CREDENTIAL_PIPE_REQUIRED')
    raw=os.read(fd,4097);os.close(fd)
    if len(raw)>4096:raise ValueError('CREDENTIAL_FILE_TOO_LARGE')
    client=DeepSeekClient(raw.decode().strip());del raw
    return client


def validate_price_freshness(plan,*,now=None):
    now=time.time() if now is None else now
    stamp=plan.get('prices_checked_unix')
    if type(stamp) is not int or not 0<=now-stamp<=86400:raise ValueError('PRICING_REVALIDATION_REQUIRED')


def load_plan(pin):
    try:raw=(ROOT/'phase22_experiment.json').read_bytes()
    except OSError:raise ValueError('FROZEN_PLAN_UNAVAILABLE') from None
    if type(pin) is not str or hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('EXACT_FROZEN_PLAN_PIN_REQUIRED')
    plan=strict_json(raw)
    if (plan.get('model')!='deepseek-v4-pro' or plan.get('requests_per_task')!=2
            or plan.get('maximum_requests')!=12 or plan.get('maximum_input_token_estimate')!=16384
            or plan.get('maximum_output_tokens')!=4096 or plan.get('request_deadline_seconds')!=120):
        raise ValueError('FROZEN_BUDGET_CHANGED')
    for name,sha in plan['frozen_files'].items():
        path=ROOT/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('FROZEN_IMPLEMENTATION_OR_TASK_CHANGED')
    from phase22_repair import catalog
    if plan['cases']!=[s['id'] for s in catalog().tasks()]:raise ValueError('FROZEN_TASK_IDENTITIES_CHANGED')
    return plan


def run_experiment(pin,authorization,credential_fd,output):
    # Refuse absent owner authority BEFORE credential consumption or network.
    grant=read_grant(authorization)
    plan=load_plan(pin);validate_price_freshness(plan)
    client=read_client(credential_fd)
    began=time.monotonic();cpu=time.process_time();record=None
    def stopped(*_):raise KeyboardInterrupt
    old_term=signal.signal(signal.SIGTERM,stopped)
    try:
        validate_grant(grant,pin,client.account_sha256)
        # A single fixed private local store. Missing/corrupt state is never
        # interpreted as remaining remote quota or account-global persistence.
        STORE.mkdir(mode=0o700,exist_ok=True)
        with Budget(STORE,grant,pin,client.account_sha256) as budget:
            if budget.status()['reserved_requests']:
                raise ValueError('PERSISTED_REQUESTS_REQUIRE_RECONCILIATION_NO_AUTOMATIC_REPLAY')
            if (STORE/'STOP').exists():raise ValueError('EXPERIMENT_STOPPED')
            before=client.inspect()
            if plan['model'] not in admitted_models(before['models']):raise ValueError('SELECTED_MODEL_UNAVAILABLE')
            destination=Path(output)
            if destination.exists():raise ValueError('FRESH_RESULT_DESTINATION_REQUIRED')
            destination.mkdir(parents=True,mode=0o700)
            from phase22_repair import OwnedSession,messages
            service=OwnedSession()
            record={'kind':'PHASE22_DEEPSEEK_OWNED_EXPERIMENT','plan_sha256':pin,'model':plan['model'],
                    'provider':'https://api.deepseek.com','authorship_basis':'authenticated_provider_response',
                    'classification':'OWNED_DEVELOPMENT','independent_evaluation':False,
                    'commercial_admission':'NOT_ADMITTED','customer_execution_authorized':False,
                    'delivery_authorized':False,'provider_confirmed_cost':False,
                    'before':before,'runtime_admission':service.proof,'cases':[],
                    'status':'RUNNING','additional_cash_spending_usd':0,'credit_consumption_usd':None}
            write_receipt(destination/'experiment.json',record)
            try:
                for case in plan['cases']:
                    if (STORE/'STOP').exists():raise ValueError('EXPERIMENT_STOPPED')
                    task=service.prepare(case);row={'case_id':case,'task':task,'attempts':[]};record['cases'].append(row)
                    previous=None
                    for _ in range(2):
                        entry={}
                        try:
                            response=client.generate(budget,case,messages(task,previous),plan['model'])
                            entry['generation']=dict(client.last_evidence)
                            verification=service.submit(task,response['content'])
                            entry['verification']=verification;previous=verification;task=service.current(case)
                        except ValueError as error:
                            code=str(error) if re.fullmatch('[A-Z_]{1,100}',str(error)) else 'BOUNDED_OPERATION_FAILED'
                            entry.update(diagnostic=code,generation=dict(client.last_evidence or {}))
                            row['attempts'].append(entry);write_receipt(destination/'experiment.json',record)
                            # Unknown/malformed provider routes stop the experiment;
                            # no automatic retry or budget refund after uncertainty.
                            raise ValueError(code) from None
                        row['attempts'].append(entry);write_receipt(destination/'experiment.json',record)
                        if verification['independently_verified'] or verification['state']=='BLOCKED':break
                    row['verified']=bool(previous and previous['independently_verified'])
                record['status']='COMPLETED'
            except (KeyboardInterrupt,SystemExit):record['status']='INTERRUPTED'
            except Exception as error:
                record['status']='BLOCKED';record['diagnostic']=str(error) if re.fullmatch('[A-Z_]{1,100}',str(error)) else 'TRUSTED_CONTROLLER_FAILURE'
            finally:
                record['budget']=budget.status()
                try:
                    after=client.call('GET','/user/balance');record['after_balance']=after
                    delta=microusd(usd_balance(before['balance']))-microusd(usd_balance(after))
                    record['observed_account_balance_delta_microusd']=delta
                    record['balance_delta_attribution']='Account-wide delta; unrelated activity cannot be excluded'
                except ValueError:record['after_balance_status']='UNAVAILABLE'
                record['elapsed_seconds']=round(time.monotonic()-began,3)
                record['trusted_controller_cpu_seconds']=round(time.process_time()-cpu,3)
                record['trusted_controller_peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
                record['provider_cpu_memory']='NOT_EXPOSED_BY_API'
                record['inference_requests_reserved']=budget.status()['reserved_requests']
                record['actual_http_completion_attempts']=client.completion_requests_dispatched
                write_receipt(destination/'experiment.json',record)
        return record
    finally:
        client.close();signal.signal(signal.SIGTERM,old_term)


def prepare(output):
    from phase22_repair import OwnedSession,catalog
    service=OwnedSession();rows=[]
    for spec in catalog().tasks():
        task=service.prepare(spec['id']);rows.append({'case_id':spec['id'],'task':task,'baseline':service.sessions[spec['id']]['baseline']})
    record={'kind':'PHASE22_OWNED_BASELINE_PREPARATION','cases':rows,'runtime_admission':service.proof,
            'actual_inference_requests':0,'model_accuracy':'UNMEASURED','commercial_admission':'NOT_ADMITTED'}
    write_receipt(output,record);return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--output',type=Path,required=True)
    inspect=sub.add_parser('inspect');inspect.add_argument('--credential-fd',type=int,required=True);inspect.add_argument('--output',type=Path,required=True)
    live=sub.add_parser('run');live.add_argument('--plan-sha256',required=True)
    live.add_argument('--authorization',type=Path,required=True);live.add_argument('--credential-fd',type=int,required=True);live.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='prepare':
            r=prepare(args.output);print(json.dumps({'prepared':len(r['cases']),'actual_inference_requests':0}));return 0
        if args.command=='inspect':
            client=read_client(args.credential_fd)
            try:r=client.inspect()
            finally:client.close()
            r.update(kind='PHASE22_READ_ONLY_ACCOUNT_CHECK',credential_persisted=False,checked_at_unix=int(time.time()))
            write_receipt(args.output,r);print(json.dumps({'status':'READ_ONLY_ACCOUNT_VERIFIED','actual_inference_requests':0}));return 0
        r=run_experiment(args.plan_sha256,args.authorization,args.credential_fd,args.output)
        print(json.dumps({'status':r['status'],'actual_reserved_requests':r['inference_requests_reserved']}))
        return 0 if r['status']=='COMPLETED' else 1
    except Exception as error:
        code=str(error) if re.fullmatch('[A-Z_]{1,100}',str(error)) else 'TRUSTED_OPERATION_FAILED'
        print(json.dumps({'status':'BLOCKED','diagnostic':code}));return 1


if __name__=='__main__':raise SystemExit(main())
