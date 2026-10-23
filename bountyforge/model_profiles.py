"""Fixed local model identities. Selection never changes engine or provider."""
DEFAULT_PROFILE='QWEN_1_5B'
PROFILES=('QWEN_1_5B','QWEN_7B','QWEN35_4B','GRANITE42_3B')
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
    'QWEN35_4B':{'id':'QWEN35_4B','label':'Qwen3.5 4B (research)',
        'filename':'Qwen3.5-4B-Q4_K_M.gguf',
        'sha256':'00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4',
        'revision':'e87f176479d0855a907a41277aca2f8ee7a09523','license':'Apache-2.0','experimental':True,
        'repository':'unsloth/Qwen3.5-4B-GGUF','bytes':2740937888,'thinking_disabled':True,
        'upstream_repository':'Qwen/Qwen3.5-4B','upstream_revision':'851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a',
        'provenance':'Quantizer-declared official base; conversion revision/attestation unavailable'},
    'GRANITE42_3B':{'id':'GRANITE42_3B','label':'IBM Granite 4.2 3B (research)',
        'filename':'granite-4.2-3b-Q4_K_M.gguf',
        'sha256':'e0406663965846ae22a403456eb826ccce5f450840491f71952f18a7cb78e7d5',
        'revision':'c40945d71cd90f249a56985e8155551a9188dc30','license':'Apache-2.0','experimental':True,
        'repository':'ibm-granite/granite-4.2-3b-GGUF','bytes':2244011552,'thinking_disabled':True,
        'upstream_repository':'ibm-granite/granite-4.2-3b','upstream_revision':'4e9c275e232f10211ec88644d106a1f6a1b60e06',
        'provenance':'IBM-published GGUF; no signed conversion provenance established'},
}


def profile_spec(profile=DEFAULT_PROFILE):
    if type(profile) is not str or profile not in PROFILES:raise ValueError('UNKNOWN_LOCAL_MODEL_PROFILE')
    return {**_SPECS[profile],'context_tokens':2048,'threads':2,'parallel_streams':1,
            'supported_cpu_threads':[2,4],
            'max_prompt_tokens':700 if profile=='QWEN_7B' else 1898,
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
