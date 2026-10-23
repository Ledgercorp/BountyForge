"""Replay queue receipts using Phase12's unchanged candidate-verification gate."""
from bountyforge.phase12_replay import replay_recording
from bountyforge.repair_engines import digest, encoded, strict_json, receipt_hash, RepairRejected


def replay_queue_recording(raw,expected_sha256,*,verifier=None):
    if type(raw) is not bytes or len(raw)>500000 or digest(raw)!=expected_sha256:
        raise RepairRejected('QUEUE_RECORDING_DIGEST_REJECTED')
    recording=strict_json(raw);calls=recording.get('calls')
    if type(calls) is not list or not 1<=len(calls)<=30:raise RepairRejected('BOUNDED_QUEUE_RECORDING_REQUIRED')
    normalized=[]
    for call in calls:
        result=call.get('response',{}).get('result',{})
        if result.get('isError') is not False:continue
        content=result.get('content',[])
        if len(content)!=1 or content[0].get('type')!='text':raise RepairRejected('AMBIGUOUS_QUEUE_RESPONSE')
        value=strict_json(content[0]['text'])
        if call['tool']=='claim_owned_queue' and 'task' in value:
            tool='prepare_owned_repair';payload=value['task']
        elif call['tool']=='submit_owned_queue' and value.get('state')=='VERIFIED':
            tool='submit_owned_repair';payload=value['receipt']
        else:continue
        normalized.append({'tool':tool,'response':{'result':{'isError':False,
                          'content':[{'type':'text','text':encoded(payload).decode()}]}}})
    derived=encoded({'calls':normalized})
    report=replay_recording(derived,digest(derived),verifier=verifier)
    report.update(kind='phase13_queue_candidate_independent_replay',queue_recording_sha256=expected_sha256)
    report['receipt_sha256']=receipt_hash(report)
    return report
