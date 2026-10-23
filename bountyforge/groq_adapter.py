"""Opt-in Groq GPT-OSS adapter for owned-fixture-only BountyForge evaluation.

Never put a write token in this process. No automatic fallback, billing,
job submission, commands, or third-party repository execution is permitted.
"""
from __future__ import annotations
import copy
import json
import os
import urllib.request
import urllib.error
import time

URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL_ID = 'openai/gpt-oss-120b'
MAX_CALLS = 8
MAX_RESPONSE_BYTES = 65536


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('External model redirects prohibited')


class HostedGroqModel:
    """Works with propose_lines; only explicit owner-authorized owned inputs."""

    def __init__(self, *, total_generation_tokens=150, minimum_interval_seconds=0):
        if (os.environ.get('BOUNTYFORGE_GROQ_FREE_PLAN_ATTESTED') != '1'
                or not os.environ.get('GROQ_API_KEY')):
            raise ValueError('Hosted Groq model not enabled or Free Plan not attested')
        if (type(total_generation_tokens) is not int or total_generation_tokens not in {150,1024}
                or type(minimum_interval_seconds) is not int or not 0 <= minimum_interval_seconds <= 60):
            raise ValueError('Unapproved hosted resource budget')
        self._key = os.environ['GROQ_API_KEY']
        self.last_call = None
        self.calls = 0
        self.total_generation_tokens=total_generation_tokens
        self.minimum_interval_seconds=minimum_interval_seconds
        self._last_request=None
        self._disabled=False

    @staticmethod
    def _lines(prompt):
        if not isinstance(prompt, str) or len(prompt.encode('utf-8')) > 3600:
            raise ValueError('Invalid bounded prompt')
        try:
            values = json.loads(prompt)['editable_lines']
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Missing trusted line scope') from exc
        if (not isinstance(values, list) or not 1 <= len(values) <= 30
                or any(type(x) is not int or x < 1 for x in values)
                or len(set(values)) != len(values)):
            raise ValueError('Invalid trusted line scope')
        return sorted(values)

    def complete_line(self, system, user, max_tokens=125):
        self.last_call=None
        from bountyforge.lineedit import LINE_SCHEMA
        lines = self._lines(user)
        schema = copy.deepcopy(LINE_SCHEMA)
        schema['properties']['changes']['items']['properties']['line']['enum'] = lines
        return self._complete(system, user, max_tokens, schema, 'bounded_line_patch')

    def complete_diagnosis(self, system, user, max_tokens=125):
        self.last_call=None
        lines = self._lines(user)
        schema = {'type': 'object', 'properties': {
            'lines': {'type': 'array', 'minItems': 1, 'maxItems': 3,
                      'uniqueItems': True, 'items': {'type': 'integer', 'enum': lines}},
            'reason': {'type': 'string', 'maxLength': 400},
        }, 'required': ['lines', 'reason'], 'additionalProperties': False}
        return self._complete(system, user, max_tokens, schema, 'bounded_line_diagnosis')

    def _complete(self, system, user, max_tokens, schema, name):
        self.last_call = None
        if (not isinstance(system, str) or len(system.encode('utf-8')) > 3600
                or type(max_tokens) is not int or not 1 <= max_tokens <= 150):
            raise ValueError('Invalid generation budget')
        if self._key in system or self._key in user:
            raise ValueError('Credential detected in model context')
        if self._disabled:
            raise RuntimeError('Hosted inference instance disabled; no retry or fallback')
        if self.calls >= MAX_CALLS:
            raise RuntimeError('Hosted inference call budget exhausted')
        if self._last_request is not None:
            remaining=self.minimum_interval_seconds-(time.monotonic()-self._last_request)
            if remaining>0:time.sleep(min(remaining,60))
        self._last_request=time.monotonic()
        self.calls += 1  # Count before making HTTP request; no automatic retries.
        total_limit=1024 if self.total_generation_tokens==1024 else max_tokens
        payload = json.dumps({
            'model': MODEL_ID,
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': user}],
            'max_completion_tokens': total_limit,
            'reasoning_effort': 'low', 'include_reasoning': False,
            'temperature': 0,
            'stream': False,
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': name, 'strict': True, 'schema': schema}},
        }).encode('utf-8')
        req = urllib.request.Request(URL, data=payload, method='POST', headers={
            'Content-Type': 'application/json',
            'User-Agent': 'BountyForge-Owned-Canary/1',
            'Authorization': 'Bearer ' + self._key,
        })
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with opener.open(req, timeout=30) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError('Response over budget')
            if self._key.encode() in raw:
                raise ValueError('Provider echoed a credential')
            result = json.loads(raw)
            if result.get('model',MODEL_ID) != MODEL_ID:
                raise ValueError('Unexpected provider model identity')
            choice = result['choices'][0]
            answer = choice['message']['content']
            if choice.get('finish_reason') != 'stop':
                raise ValueError('Incomplete hosted model response')
            if not isinstance(answer, str) or not answer.strip() or len(answer.encode()) > 3000:
                raise ValueError('Invalid hosted model response')
            json.loads(answer)
            usage = result.get('usage') or {}
            def counter(value):
                return value if type(value) is int and value >= 0 else None
            details=usage.get('completion_tokens_details') or {}
            self.last_call = {'finish_reason': 'stop',
                              'completion_tokens': counter(usage.get('completion_tokens')),
                              'prompt_tokens': counter(usage.get('prompt_tokens')),
                              'total_tokens': counter(usage.get('total_tokens')),
                              'requested_max_completion_tokens': total_limit,
                              'reasoning_tokens': counter(details.get('reasoning_tokens')),
                              'provider_model_reported':result.get('model'),
                              'provider': 'groq', 'model': MODEL_ID}
            return answer.strip()
        except urllib.error.HTTPError as exc:
            self._disabled=True
            # Only disclose exact, documented permission codes. Never include
            # untrusted status text, message, body, headers, prompt, or key.
            status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else 0
            reason = 'unclassified'
            if status == 403:
                try:
                    raw_error = exc.read(4097)
                    if len(raw_error) <= 4096:
                        provider_error = json.loads(raw_error)
                        if isinstance(provider_error, dict):
                            record = provider_error.get('error')
                            code = record.get('code') if isinstance(record, dict) else None
                            if code in ('model_permission_blocked_org',
                                        'model_permission_blocked_project'):
                                reason = code
                except (ValueError, TypeError, OSError):
                    pass
            raise RuntimeError(
                f'Hosted inference unavailable or rejected (http_{status}, provider_code_{reason}); no retry or fallback'
            ) from None
        except Exception:
            self._disabled=True
            # Never echo HTTP errors, request bodies, prompts or API credentials.
            raise RuntimeError('Hosted inference unavailable or rejected; no retry or fallback') from None
