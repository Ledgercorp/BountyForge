"""Fixed optional Granite entrypoint; gateway/limits are shared with Phase20."""
import json
from pathlib import Path
import sys
sys.path.insert(0,'/workspace')
from phase20_model_service import serve


def main():
    config=json.loads(Path('/workspace/model-config.json').read_text())
    if (set(config)!={'grammar','request_limit','pi_ai_context_guard_compat'}
            or type(config['grammar']) is not str or len(config['grammar'])>50000
            or config['request_limit']!=2 or config['pi_ai_context_guard_compat'] is not True):
        raise ValueError('FIXED_GRANITE_OWNED_CONFIG_REQUIRED')
    serve(config,model_id='bountyforge-granite-3b',disable_thinking=True)


if __name__=='__main__':main()
