"""Fixed local model identities. Selection never changes engine or provider."""
DEFAULT_PROFILE='QWEN_1_5B'
PROFILES=('QWEN_1_5B','QWEN_7B')
RUNTIME_SHA256='152e33221c9c9d37816a8ee9943f8d87339199197c80cb692559c9756b2027d8'
_SPECS={
    'QWEN_1_5B':{'id':'QWEN_1_5B','label':'Qwen Coder 1.5B (default)',
        'filename':'qwen2.5-coder-1.5b-instruct-q4_k_m.gguf',
        'sha256':'cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046',
        'revision':None,'license':'Apache-2.0','experimental':False},
    'QWEN_7B':{'id':'QWEN_7B','label':'Qwen Coder 7B (experimental)',
        'filename':'qwen2.5-coder-7b-instruct-q4_k_m.gguf',
        'sha256':'509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c',
        'revision':'13fb94bfda8c8cf22497dc57b78f391a9acb426a','license':'Apache-2.0','experimental':True},
}


def profile_spec(profile=DEFAULT_PROFILE):
    if type(profile) is not str or profile not in PROFILES:raise ValueError('UNKNOWN_LOCAL_MODEL_PROFILE')
    return {**_SPECS[profile],'context_tokens':2048,'threads':2,'parallel_streams':1,
            'paid_fallback':False,'runtime_sha256':RUNTIME_SHA256}


def select_profile(engine,profile=None):
    if engine=='CODEX_AGENT':
        if profile is not None:raise ValueError('CODEX_IS_NOT_A_QWEN_PROFILE')
        return None
    if engine!='QWEN_LOCAL':raise ValueError('UNKNOWN_REPAIR_ENGINE')
    return profile_spec(DEFAULT_PROFILE if profile is None else profile)['id']


def endpoint_matches(props,model_path):
    return (type(props) is dict and props.get('model_path')==str(model_path)
            and type(props.get('total_slots')) is int and props['total_slots']==1
            and type(props.get('default_generation_settings')) is dict
            and props['default_generation_settings'].get('n_ctx')==2048)
