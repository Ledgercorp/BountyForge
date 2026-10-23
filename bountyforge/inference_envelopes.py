"""Named, fixed experiment envelopes. Never accept arbitrary resource limits."""
ENVELOPES = {
    'LEGACY': {'cpu_seconds':180,'wall_seconds':180,'request_seconds':45,'completion_tokens':150},
    'NEXTGEN_TRIAL': {'cpu_seconds':600,'wall_seconds':240,'request_seconds':75,'completion_tokens':256},
}


def envelope_spec(name='LEGACY'):
    if type(name) is not str or name not in ENVELOPES:raise ValueError('UNKNOWN_RESOURCE_ENVELOPE')
    return {'id':name,**ENVELOPES[name],'address_space_bytes':10*1024**3,'context_tokens':2048,
            'maximum_threads':4,'parallel_streams':1,'log_bytes':1024*1024}
