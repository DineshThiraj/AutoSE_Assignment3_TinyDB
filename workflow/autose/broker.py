"""Fresh requests, inert inputs and an opt-in API adapter. No target execution."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import GateError, ROLE_IDENTITY, budget, digest, encoded, require


def live_preflight(config, *, require_key=True):
    require(config.get('enabled') is True, 'hosted provider disabled under deferred ADR-006')
    require(config.get('adapter') == 'openai-responses', 'provider adapter not selected/supported')
    for key in ('model', 'effort', 'provider_support_evidence', 'hard_cap_evidence', 'paid_authorization_evidence'):
        require(isinstance(config.get(key), str) and config[key].strip(), f'missing {key}')
    require(config.get('provider_cap_verified') is True, 'provider-enforced hard cap not verified')
    require(config.get('paid_authorized') is True, 'separate paid authorization missing')
    require(isinstance(config.get('authorization_expires_at'), (int, float)) and time.time() < config['authorization_expires_at'], 'paid authorization expired')
    require(0 < config.get('max_output_tokens', 0) <= 16000, 'response token bound missing')
    require(0 < config.get('token_budget', 0) <= 1_000_000, 'global token budget missing')
    require(config.get('effort') in {'low', 'medium', 'high', 'xhigh'}, 'unverified reasoning setting')
    if require_key:
        require(os.environ.get('AUTOSE_MODEL_API_KEY'), 'model repository secret not supplied')
    # These evidence locators must be checked by a person before enabling this
    # configuration on protected main. This function cannot enforce provider billing.
    return True


class ResponsesBroker:
    """Optional protocol adapter, not a provider/model choice or availability claim.

    Schema reference checked 2026-11-17:
    https://developers.openai.com/api/reference/resources/responses/methods/create
    No retry or fallback provider/model is implicit.
    """

    def __init__(self, config):
        live_preflight(config)
        self.config = config

    def ask(self, state, role, instruction, context):
        require(state['execution_kind'] == 'hosted', 'live broker forbidden in fixture execution')
        payload = encoded(context)
        max_output = self.config['max_output_tokens']
        budget(state, reserve_output=len(payload.encode()) + len(instruction.encode()) + max_output + 2000)
        require(len(payload.encode()) < 800_000, 'model input size ceiling')
        state['usage']['calls'] += 1
        state['usage']['unknown'] = True  # Preserve uncertain spend if the call fails.
        require(role in ROLE_IDENTITY, 'unknown reasoning role/stage')
        trace = {'role':ROLE_IDENTITY[role],'stage':role,'model':self.config['model'],'effort':self.config['effort'],
                 'input_hash':digest(payload),'usage':None,'status':'request_started'}
        state.setdefault('calls', []).append(trace)
        request_body = {
            'model': self.config['model'], 'store': False,
            'reasoning': {'effort': self.config['effort']},
            'max_output_tokens': max_output,
            'text': {'format': {'type': 'json_object'}},
            'instructions': instruction,
            'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': payload}]}],
        }
        req = urllib.request.Request('https://api.openai.com/v1/responses',
            data=encoded(request_body).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + os.environ['AUTOSE_MODEL_API_KEY'], 'Content-Type': 'application/json'})
        started = time.monotonic()
        try:
            # urllib does not follow a caller-selected endpoint; never send credentials
            # to model-supplied URLs. Refuse redirects rather than forwarding headers.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            with urllib.request.build_opener(NoRedirect()).open(req, timeout= min(900, max(1, 2400 - (time.time() - state['started_at'])))) as response:
                raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, 'provider response too large')
            body = json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            # Do not save provider bodies, exception reprs, headers or request objects.
            raise GateError('provider request failed; usage unknown; no automatic retry') from None
        trace.update(seconds=time.monotonic()-started, provider_response_id=body.get('id'),status=body.get('status'))
        usage = body.get('usage') or {}
        require(all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens', 'total_tokens')), 'provider usage unavailable')
        require(usage['total_tokens'] == usage['input_tokens'] + usage['output_tokens'], 'inconsistent provider usage')
        state['usage']['tokens'] += usage['total_tokens']
        state['usage']['unknown'] = False
        trace['usage'] = usage
        require(state['usage']['tokens'] <= state['limits']['tokens'], 'provider exceeded token ceiling')
        require(body.get('status') == 'completed', 'provider response incomplete/refused')
        output = ''.join(part['text'] for item in body.get('output', []) if item.get('type') == 'message'
                         for part in item.get('content', []) if part.get('type') == 'output_text')
        require(output, 'no structured model output')
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            raise GateError('model returned invalid JSON') from None
        require(isinstance(value, dict), 'model JSON must be an object')
        require(len(encoded(value).encode()) < 300_000, 'model output size ceiling')
        return value


def context(state, role, repo):
    """Explicit role inputs; never hand a reviewer the accumulated run state."""
    if role == 'review':
        return {'issue': state['issue'], 'diff': state['patch'], 'source': state['source']}
    result = {'issue': state['issue'], 'authorization': state['authorization'], 'source': state['source']}
    if role == 'requirements':
        result['A1_skill'] = (Path(repo) / 'reuse/A1_REQUIREMENTS_SKILL.md').read_text()
    else:
        result['specification'] = state['spec']
        result['A2_architecture'] = (Path(repo) / 'reuse/A2_ARCHITECTURE.md').read_text()
    if role in {'implementation', 'testing'}:
        result['design'] = state['design']
        result['repair_feedback'] = state.get('feedback')
        result['previous_test_failure'] = state.get('execution', {}).get('log', '')[-12000:]
    return result


def ask(broker, state, role, repo, *, semantic_input=None):
    prompt_name = 'semantic' if semantic_input is not None else role
    instruction = (Path(repo) / 'workflow/prompts' / (prompt_name + '.txt')).read_text()
    inputs = semantic_input if semantic_input is not None else context(state, role, repo)
    return broker.ask(state, role, instruction, inputs)
