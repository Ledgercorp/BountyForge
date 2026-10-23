"""TEST-ONLY fixed owned repair driver. No customer or live model capability.

Only four enum scenarios and empty stdin are accepted. The model adapter uses
one separate Python process per simulated response, with a constant backend
program; neither source, paths, credentials nor executable commands are inputs.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from bountyforge.repair_session import repair_owned
from bountyforge.worker import FIXTURE_MARKER, _run_tests

SCENARIOS = ('healthy', 'invalidproposal', 'wrongcandidate', 'providerfailure')
SOURCE = b'def scaled(value):\n    total = (\n        value * 2\n    )\n    return total\n'
TESTS = b'import unittest\nfrom subject import scaled\nFACTOR = 3\nclass Contract(unittest.TestCase):\n def test_scaled(self):\n  self.assertEqual(scaled(4), 4 * FACTOR)\n def test_zero(self):\n  self.assertEqual(scaled(0), 0)\n'
MARKER = b'owned-test-driver-only'
HEALTHY = b'def scaled(value):\n    total = value * 3\n    return total\n'
WRONG = b'def scaled(value):\n    total = value * 4\n    return total\n'
PINS = {
    'subject.py': 'c52e8a84118f353f5c6c26febd1fd69f24cd2161b60cfbe0a3a54a9f65a5b72a',
    'tests/test_regression.py': '28827228f55cde073b97bf17a663c57b9d97a1c3a3e36b80363064cc34149e02',
}
ENV = {'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'}
# A constant owned process program, never assembled from response/input text.
BACKEND = r'''
import json,sys
scenario=sys.argv[1]
raw=sys.stdin.buffer.read(16385)
try:
    request=json.loads(raw)
    prompt=json.loads(request['prompt'])
    assert len(raw)<=16384 and set(request)=={'system','prompt','max_tokens'}
    assert isinstance(request['system'],str) and type(request['max_tokens']) is int
    assert prompt['edit_protocol']=='owned_statement_session_v8'
    assert prompt['approved_file']=='subject.py' and prompt['target_symbol']=='scaled'
except Exception:
    raise SystemExit(2)
if scenario=='providerfailure':
    print('OWNED_PROVIDER_FAILURE_DETAIL',file=sys.stderr)
    raise SystemExit(2)
if scenario=='invalidproposal':
    response='not-json'
elif scenario=='healthy':
    response=json.dumps({'changes':[{'line':2,'new':'total = value * 3'}]})
elif scenario=='wrongcandidate':
    response=json.dumps({'changes':[{'line':2,'new':'total = value * 4'}]})
else:
    raise SystemExit(2)
print(json.dumps({'provider_simulator':True,'live_model_calls':0,'response':response}))
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(scenario):
    actual_runs = []
    backend_receipts = []
    class SimulatedBackend:
        calls = 0
        last_call = None

        def complete_line(self, system, prompt, max_tokens):
            self.calls += 1
            completed = subprocess.run([sys.executable, '-I', '-c', BACKEND, scenario],
                input=json.dumps({'system':system, 'prompt':prompt, 'max_tokens':max_tokens}).encode(),
                env=ENV, capture_output=True, timeout=3)
            backend_receipts.append({'exit_code':completed.returncode,
                'prompt_sha256':sha(prompt.encode()), 'stdout_sha256':sha(completed.stdout),
                'stderr_sha256':sha(completed.stderr)})
            if completed.returncode or completed.stderr or len(completed.stdout) > 4096:
                raise RuntimeError('Owned simulated provider unavailable')
            response = json.loads(completed.stdout)
            if response.get('provider_simulator') is not True or response.get('live_model_calls') != 0:
                raise RuntimeError('Owned simulated provider unavailable')
            self.last_call = {'provider_simulator':True, 'live_model_calls':0}
            return response['response']

    def runner(root):
        root = Path(root)
        source = (root / 'subject.py').read_bytes()
        if (source not in (SOURCE, HEALTHY, WRONG)
                or (root / 'tests/test_regression.py').read_bytes() != TESTS
                or (root / FIXTURE_MARKER).read_bytes() != MARKER):
            raise RuntimeError('Owned test-driver fixture changed')
        receipt = _run_tests(root)
        role = 'baseline' if source == SOURCE else 'independent' if root.name == 'independent' else 'candidate'
        actual_runs.append(dict(receipt, role=role, source_sha256=sha(source)))
        return receipt

    with tempfile.TemporaryDirectory(prefix='bf-phase8-test-driver-') as directory:
        root = Path(directory)
        (root / 'tests').mkdir(mode=0o700)
        for path, raw in ((root / 'subject.py', SOURCE),
                          (root / 'tests/test_regression.py', TESTS),
                          (root / FIXTURE_MARKER, MARKER)):
            path.write_bytes(raw); path.chmod(0o600)
        if sha(SOURCE) != PINS['subject.py'] or sha(TESTS) != PINS['tests/test_regression.py']:
            raise RuntimeError('Fixed owned test-driver pins changed')
        model = SimulatedBackend()
        session = repair_owned({'verification':'unverified_candidate', 'target_symbol':'scaled',
            'description_excerpt':'Apply the stated scale while preserving zero.'},
            root, 'subject.py', model, expected_hashes=PINS, test_runner=runner, max_attempts=2)
        unchanged = ((root / 'subject.py').read_bytes() == SOURCE
                     and (root / 'tests/test_regression.py').read_bytes() == TESTS)
    return {'kind':'phase8_repair_component_TEST_DRIVER', 'test_driver_only':True,
        'provider_simulator':True, 'live_model_calls':0, 'model_calls':0,
        'simulated_model_calls':session['model_calls'], 'simulated_backend_processes':model.calls,
        'backend_requests':model.calls, 'session_model_calls_are_simulated':True,
        'received_revenue_usd':0, 'customer_execution_authorized':False,
        'customer_source_accepted':False, 'customer_environment_tested':False,
        'customer_rights_verified':False, 'owner_consent_verified':False,
        'real_payment_verified':False, 'launch_enabled':False,
        'delivery_authorized':False, 'production_ready':False,
        'original_fixture_unchanged':unchanged, 'expected_candidate_sha256':sha(HEALTHY),
        'actual_test_runs':actual_runs, 'backend_receipts':backend_receipts, 'session':session}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS or sys.stdin.buffer.read(257):
        print('Owned TEST-DRIVER input rejected', file=sys.stderr)
        return 2
    report = run(sys.argv[1])
    print(json.dumps(report, sort_keys=True))
    return 0 if report['session']['status'] == 'review_ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
