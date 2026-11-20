"""Fresh requests, inert inputs and an opt-in API adapter. No target execution."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import GateError, ROLE_IDENTITY, SECRET_PATTERN, budget, digest, encoded, require
from .trial import Ledger, PHASE_CALLS, identity, preflight, response_cost, usd
from .github import GitHub


def live_preflight(config, *, require_key=True):
    require(config.get('enabled') is True, 'hosted provider disabled under deferred ADR-006')
    require(config.get('adapter') == 'openai-responses', 'provider adapter not selected/supported')
    for key in ('model', 'effort', 'provider_support_evidence', 'hard_cap_evidence', 'paid_authorization_evidence'):
        require(isinstance(config.get(key), str) and config[key].strip(), f'missing {key}')
    require(config.get('provider_cap_verified') is True, 'provider-enforced hard cap not verified')
    require(config.get('paid_authorized') is True, 'separate paid authorization missing')
    require(isinstance(config.get('authorization_expires_at'), (int, float)) and time.time() < config['authorization_expires_at'], 'paid authorization expired')
    require(type(config.get('max_output_tokens')) is int and 0 < config['max_output_tokens'] <= 16000, 'response token bound missing')
    require(type(config.get('token_budget')) is int and 0 < config['token_budget'] <= 25_584_000, 'global token budget missing')
    require(config.get('effort') in {'low', 'medium', 'high', 'xhigh'}, 'unverified reasoning setting')
    if require_key:
        require(os.environ.get('AUTOSE_MODEL_API_KEY'), 'model repository secret not supplied')
    preflight(config)
    # These evidence locators must be checked by a person before enabling this
    # configuration on protected main. This function cannot enforce provider billing.
    return True


class ResponsesBroker:
    """Optional protocol adapter, not a provider/model choice or availability claim.

    Schema reference checked 2026-11-17:
    https://developers.openai.com/api/reference/resources/responses/methods/create
    No retry or fallback provider/model is implicit.
    """

    def __init__(self, config, *, ledger=None, phase=None, consumer=None):
        live_preflight(config)
        self.config = config
        self.ledger = ledger if ledger is not None else Ledger(GitHub())
        self.phase = phase
        self.consumer = consumer

    def ask(self, state, role, instruction, context):
        require(state['execution_kind'] == 'hosted', 'live broker forbidden in fixture execution')
        require(self.phase in PHASE_CALLS, 'paid phase grant required')
        identity(state, self.config)
        grant = self.ledger.verify(state, self.config, self.phase)
        require(role == {'author-tests':'testing','review-final':'review'}.get(self.phase,self.phase), 'role/grant mismatch')
        grant_sha = state['trial_grant']['sha']
        used = sum(c.get('grant_sha') == grant_sha for c in state.get('calls', []))
        require(used < grant['calls'], 'reserved phase calls exhausted')
        payload = encoded(context)
        require(not SECRET_PATTERN.search(payload) and not SECRET_PATTERN.search(instruction), 'credential-like outbound input; stop before provider input')
        max_output = self.config['max_output_tokens']
        budget(state, reserve_output=len(payload.encode()) + len(instruction.encode()) + max_output + 2000)
        require(len(payload.encode()) < 800_000, 'model input size ceiling')
        require(role in ROLE_IDENTITY, 'unknown reasoning role/stage')
        trace = {'role':ROLE_IDENTITY[role],'stage':role,'model':self.config['model'],'effort':self.config['effort'],
                 'input_hash':digest(payload),'usage':None,'status':'authorization_pending',
                 'grant_sha':grant_sha,'grant_call':used+1,'cost':None}
        state.setdefault('calls', []).append(trace)
        request_body = {
            'model': self.config['model'], 'store': False,
            'service_tier':'default',
            'reasoning': {'effort': self.config['effort']},
            'max_output_tokens': max_output,
            'text': {'format': {'type': 'json_object'}},
            'instructions': instruction,
            'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': payload}]}],
        }
        # The remote call slot, not this checkpoint's counter, is authoritative.
        # Any duplicate/lost consume response burns the slot and stops before HTTP.
        from .consumption import CallConsumer, call_request
        consumer = self.consumer if self.consumer is not None else CallConsumer(self.config, self.ledger)
        consumption = call_request(state, grant, self.phase, used+1, digest(encoded(request_body)))
        trace['consumption'] = consumer.consume(consumption)
        trace['status'] = 'authorized_not_sent'
        req = urllib.request.Request('https://api.openai.com/v1/responses',
            data=encoded(request_body).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + os.environ['AUTOSE_MODEL_API_KEY'], 'Content-Type': 'application/json',
                     'OpenAI-Project':self.config['trial']['project_id']})
        # Recheck after remote ledger reads, immediately before the only paid I/O.
        preflight(self.config)
        started = time.monotonic()
        try:
            # urllib does not follow a caller-selected endpoint; never send credentials
            # to model-supplied URLs. Refuse redirects rather than forwarding headers.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            timeout = min(900, 2400-(time.time()-state['started_at']), self.config['trial']['expires_at']-time.time())
            require(timeout > 0, 'paid request deadline expired')
            state['usage']['calls'] += 1
            state['usage']['unknown'] = True
            trace['status'] = 'request_started'
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
                raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, 'provider response too large')
            body = json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            # Do not save provider bodies, exception reprs, headers or request objects.
            raise GateError('provider request failed; usage unknown; no automatic retry') from None
        require(isinstance(body,dict), 'provider response malformed; usage unknown')
        trace.update(seconds=time.monotonic()-started, provider_response_id=body.get('id'),status=body.get('status'),
                     actual_model=body.get('model'),service_tier=body.get('service_tier'),usage=body.get('usage'))
        cost = response_cost(body)
        usage = body.get('usage') or {}
        require(all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens', 'total_tokens')), 'provider usage unavailable')
        require(usage['total_tokens'] == usage['input_tokens'] + usage['output_tokens'], 'inconsistent provider usage')
        state['usage']['tokens'] += usage['total_tokens']
        trace['usage'] = usage
        trace['cost'] = cost
        state['usage']['estimated_nano_usd'] = state['usage'].get('estimated_nano_usd',0) + cost['estimated_nano_usd']
        state['usage']['estimated_usd'] = usd(state['usage']['estimated_nano_usd'])
        require(usage['input_tokens'] <= grant['input_ceiling'] and usage['output_tokens'] <= grant['max_output_tokens'], 'provider exceeded reserved request envelope')
        require(state['usage']['tokens'] <= state['limits']['tokens'], 'provider exceeded token ceiling')
        from .trial import money
        require(state['usage']['estimated_nano_usd'] <= money(self.config['trial']['max_usd']), 'estimated USD ceiling exceeded')
        state['usage']['unknown'] = False
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
