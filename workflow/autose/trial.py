"""One paid #3 trial. Write-once remote reservations; no provider credentials here.

Reservation tags are created atomically, never moved/deleted/retried. Losing a race
or losing the response to a successful write stops. Unused reservations are burned.
Only the trusted ledger job has write authority; the broker only verifies records.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .common import REPOSITORY, digest, encoded, require, sha

MODEL = 'gpt-6.1-sol'
PRICING = 'openai-gpt-6.1-sol-2026-11-17'
INPUT_CEILING = 1_050_000  # Entire documented context, not a byte/token estimate.
# USD nanounits/token: Standard LONG context including 10% regional uplift.
# Always use the larger context band/uplift, including for short/global requests.
RATES = {'ordinary':4400, 'cached':220, 'write_30m':5500, 'write_12h':11000, 'output':16500}
PHASE_CALLS = {'requirements':2, 'design':2, 'implementation':1, 'author-tests':1, 'review':1, 'review-final':1}
PREFIX = 'autose-d6-issue-3-'


def issue_scope_hash(issue):
    # Comment creation changes updated_at; it must not invalidate unchanged scope.
    return digest(encoded({k:issue.get(k) or '' for k in ('number','title','body','html_url')}))


def approval_scope_hash(config):
    t = config['trial']
    scope = {k:t.get(k) for k in ('id','repository','issue','issue_hash','actor','approved_by','trigger_not_before',
                                 'project_id','currency','max_calls','max_tokens','max_usd','expires_at')}
    scope.update({k:config.get(k) for k in ('adapter','model','effort','service_tier','max_output_tokens')})
    scope['consumer_url'] = t.get('call_consumer',{}).get('url')
    scope.update(max_seconds=2400,max_review_rounds=2,max_attempts_per_round=2)
    return digest(encoded(scope))


def integer(value, lower, upper, label):
    require(type(value) is int and lower <= value <= upper, 'invalid ' + label)
    return value


def money(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9]+(?:\.[0-9]{1,9})?', value), 'USD must be an exact decimal string')
    try:
        result = Decimal(value) * 1_000_000_000
    except InvalidOperation:
        require(False, 'invalid USD')
    require(0 < result <= 1_000_000_000_000, 'USD allowance outside 0..1000')
    return int(result)


def usd(nano):
    return format(Decimal(nano) / 1_000_000_000, '.9f')


def evidence(record, project, now):
    require(isinstance(record, dict) and record.get('verified') is True, 'student evidence unverified')
    require(record.get('project_id') == project, 'evidence project mismatch')
    require(isinstance(record.get('locator'), str) and record['locator'].strip(), 'evidence locator missing')
    require(isinstance(record.get('sha256'), str) and re.fullmatch('[a-f0-9]{64}', record['sha256']), 'evidence hash missing')
    checked, expires = record.get('checked_at'), record.get('expires_at')
    require(type(checked) in (int,float) and type(expires) in (int,float) and
            now-86400 <= checked <= now < expires <= checked+86400, 'evidence stale/expired')


def preflight(config):
    """Attestations require human verification on protected main, never model claims."""
    now = time.time()
    require(config.get('enabled') is True and config.get('paid_authorized') is True and
            config.get('provider_cap_verified') is True, 'paid trial disabled/unapproved')
    t = config.get('trial')
    require(isinstance(t, dict), 'scoped trial authorization missing')
    require(t.get('repository') == REPOSITORY and type(t.get('issue')) is int and t['issue'] == 3, 'only issue #3 authorized')
    require(isinstance(t.get('id'), str) and re.fullmatch('[a-z0-9-]{8,64}', t['id']), 'trial ID missing')
    require(t.get('actor') == 'DineshThiraj' and t.get('approved_by') == 'DineshThiraj', 'student approval/actor missing')
    require(isinstance(t.get('issue_hash'), str) and re.fullmatch('[a-f0-9]{64}', t['issue_hash']), 'approved issue hash missing')
    require(type(t.get('trigger_not_before')) in (int,float) and now-86400 <= t['trigger_not_before'] <= now, 'authorized trigger window missing/stale')
    require(isinstance(t.get('project_id'), str) and re.fullmatch('[A-Za-z0-9_-]{1,128}', t['project_id']), 'provider project missing/invalid')
    require(t.get('currency') == 'USD', 'USD approval required')
    integer(t.get('max_calls'), 1, 24, 'trial calls')
    integer(t.get('max_tokens'), 1, 24*(INPUT_CEILING+16000), 'trial tokens')
    require(t['max_tokens'] == config['token_budget'], 'token approval mismatch')
    money(t.get('max_usd'))
    require(type(t.get('expires_at')) in (int,float) and now < t['expires_at'] == config['authorization_expires_at'], 'paid approval expired/mismatched')
    for name in ('approval','provider_support','hard_cap','secret','pricing'):
        evidence(t.get(name), t['project_id'], now)
        require(t[name]['expires_at'] >= t['expires_at'], 'evidence expires before approval')
    consumer = t.get('call_consumer')
    evidence(consumer,t['project_id'],now)
    require(consumer.get('available') is True and consumer['expires_at'] >= t['expires_at'], 'call consumption service unavailable')
    from .services import https_url
    https_url(consumer.get('url'))
    require(t['approval'].get('scope_sha256') == approval_scope_hash(config), 'paid approval scope mismatch')
    support = t['provider_support']
    require(support.get('available') is True and support.get('model') == MODEL and support.get('endpoint') == 'https://api.openai.com/v1/responses', 'provider unavailable/unverified')
    cap = t['hard_cap']
    require(cap.get('enforced') is True and cap.get('currency') == 'USD', 'provider hard cap not enforced')
    require(money(cap.get('limit_usd')) <= money(t['max_usd']), 'provider cap exceeds paid approval')
    require(money(cap.get('remaining_usd')) <= money(cap['limit_usd']), 'invalid remaining provider allowance')
    require(type(cap.get('period_ends_at')) in (int,float) and cap['period_ends_at'] >= t['expires_at'], 'cap period ends during trial')
    secret = t['secret']
    require(secret.get('available') is True and secret.get('name') == 'AUTOSE_MODEL_API_KEY', 'repository secret availability unverified')
    require(t['pricing'].get('schedule') == PRICING, 'pricing evidence mismatch')
    require(config['model'] == MODEL and config.get('service_tier') == 'default', 'unsupported model/tier')
    return t


def event_guard(config, event, event_name, run_attempt):
    require(str(run_attempt) == '1', 'workflow reruns forbidden for paid trial')
    t = preflight(config)
    require(event_name == 'issue_comment' and event.get('action') == 'created', 'only approved comment trigger allowed')
    require(event.get('repository',{}).get('full_name') == REPOSITORY, 'wrong event repository')
    require(event.get('issue', {}).get('number') == 3 and 'pull_request' not in event.get('issue', {}), 'issue mismatch')
    require(event.get('sender', {}).get('login') == t['actor'] and event['sender'].get('type') == 'User', 'approved actor mismatch')
    c = event.get('comment', {})
    integer(c.get('id'),1,2**63-1,'trigger comment ID')
    require(c.get('body') == '/autose' and
            c.get('user', {}).get('login') == t['actor'], 'unapproved authorization comment')
    try:
        created = datetime.fromisoformat(c.get('created_at','').replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError):
        require(False,'comment timestamp unavailable')
    require(t['trigger_not_before'] <= created <= time.time() < t['expires_at'], 'comment outside authorized trigger window')


def identity(state, config):
    t = preflight(config)
    require(state.get('execution_kind') == 'hosted', 'fixture cannot reserve paid trial')
    require(state.get('repository') == REPOSITORY and state.get('issue', {}).get('number') == 3, 'trial issue mismatch')
    require(state.get('issue_hash') == digest(encoded(state['issue'])) and
            issue_scope_hash(state['issue']) == t['issue_hash'], 'approved issue changed')
    require(state.get('authorization', {}).get('actor') == t['actor'], 'trial actor mismatch')
    require(state.get('trigger',{}).get('kind') == 'issue_comment' and
            state['trigger'].get('actor') == t['actor'], 'admitted comment identity missing')
    integer(state['trigger'].get('comment_id'),1,2**63-1,'admitted comment ID')
    require(str(state.get('run_attempt')) == '1', 'workflow reruns forbidden for paid trial')
    require(str(state.get('run_id', '')).isdigit(), 'run ID missing')
    require(str(os.environ.get('GITHUB_RUN_ATTEMPT', '1')) == '1', 'workflow reruns forbidden for paid trial')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        require(os.environ.get('GITHUB_RUN_ID') == state['run_id'] and os.environ.get('GITHUB_REPOSITORY') == REPOSITORY, 'current runner identity mismatch')
    require(not state.get('fatal') and not state.get('usage', {}).get('unknown'), 'failed/unknown spend cannot continue')
    integer(state.get('round'),1,2,'review round')
    integer(state.get('attempt'),1,2,'implementation attempt')
    require(time.time()-state['started_at'] <= 2400, 'trial elapsed budget exhausted')
    return {'trial_id':t['id'], 'config_hash':digest(encoded(config)), 'issue_hash':t['issue_hash'],
            'issue_snapshot_hash':state['issue_hash'], 'run_id':state['run_id'], 'base_sha':sha(state['base_sha']), 'run_attempt':1,'trigger':state['trigger']}


class Ledger:
    def __init__(self, github):
        self.github = github

    def read(self, name):
        ref = self.github.repo('GET', '/git/ref/tags/' + PREFIX + name)
        commit_sha = sha(ref['object']['sha'])
        commit = self.github.repo('GET', '/git/commits/' + commit_sha)
        tree = self.github.repo('GET', '/git/trees/' + sha(commit['tree']['sha']))
        require(not tree.get('truncated') and len(tree['tree']) == 1, 'ledger tree malformed')
        entry = tree['tree'][0]
        require(entry['path'] == 'ledger.json' and entry['type'] == 'blob' and entry['mode'] == '100644', 'ledger entry malformed')
        blob = self.github.repo('GET', '/git/blobs/' + sha(entry['sha']))
        require(blob.get('encoding') == 'base64', 'ledger encoding malformed')
        data = base64.b64decode(blob['content'], validate=False)
        require(len(data) < 100_000, 'ledger too large')
        return commit_sha, json.loads(data)

    def create(self, name, record, parent=None):
        # No read-then-write replacement, update-ref, force, deletion, or retry.
        # Concurrent creators of the same ref have exactly one winner at GitHub.
        blob = self.github.repo('POST', '/git/blobs', {'content':encoded(record), 'encoding':'utf-8'})
        tree = self.github.repo('POST', '/git/trees', {'tree':[{'path':'ledger.json', 'mode':'100644', 'type':'blob', 'sha':sha(blob['sha'])}]})
        commit = self.github.repo('POST', '/git/commits', {'message':'D6 reservation ' + name, 'tree':sha(tree['sha']), 'parents':[sha(parent)] if parent else []})
        commit_sha = sha(commit['sha'])
        self.github.repo('POST', '/git/refs', {'ref':'refs/tags/' + PREFIX + name, 'sha':commit_sha})
        actual_sha, actual = self.read(name)
        require(actual_sha == commit_sha and actual == record, 'ledger write verification failed')
        return commit_sha

    def claim(self, state, config):
        record = {'identity':identity(state,config), 'kind':'claim'}
        state['trial_claim'] = self.create('claim', record)

    def reserve(self, state, config, phase, *, job_id=None):
        expected = identity(state,config)
        claim_sha, claim = self.read('claim')
        require(claim == {'identity':expected, 'kind':'claim'} and state.get('trial_claim') == claim_sha, 'trial already claimed by another run/config')
        t = config['trial']
        previous = state.get('trial_grant')
        seq, totals, parent, used_phases = 1, {'calls':0, 'tokens':0, 'nano_usd':0}, claim_sha, []
        if previous:
            parent, saved = self.read('grant-' + str(previous['sequence']))
            require(parent == previous['sha'] and saved['identity'] == expected, 'grant checkpoint mismatch')
            seq, totals = saved['sequence']+1, saved['totals']
            used_phases = saved['used_phases']
        phase_key = f"r{state['round']}a{state['attempt']}-{phase}"
        require(phase_key not in used_phases, 'phase already reserved; no extra paid attempt')
        calls = PHASE_CALLS[phase]
        tokens = calls*(INPUT_CEILING+config['max_output_tokens'])
        nano = calls*(INPUT_CEILING*max(RATES[k] for k in RATES if k != 'output') + config['max_output_tokens']*RATES['output'])
        totals = {'calls':totals['calls']+calls, 'tokens':totals['tokens']+tokens, 'nano_usd':totals['nano_usd']+nano}
        require(totals['calls'] <= t['max_calls'], 'durable call budget exhausted')
        require(totals['tokens'] <= t['max_tokens'], 'durable token budget exhausted')
        require(totals['nano_usd'] <= money(t['max_usd']), 'durable USD budget exhausted')
        record = {'kind':'grant', 'identity':expected, 'sequence':seq, 'phase':phase,
                  'round':state['round'], 'attempt':state['attempt'], 'calls':calls,
                  'call_offset':totals['calls']-calls, 'totals':totals, 'input_ceiling':INPUT_CEILING,
                  'max_output_tokens':config['max_output_tokens'], 'pricing':PRICING}
        job_id = job_id or phase
        require(isinstance(job_id,str) and re.fullmatch('[a-z0-9_-]{1,100}',job_id), 'invalid paid job identity')
        record['job_id'] = job_id
        record['used_phases'] = [*used_phases,phase_key]
        commit_sha = self.create('grant-' + str(seq), record, parent)
        state['trial_grant'] = {'sequence':seq, 'sha':commit_sha, 'reserved_totals':totals,
                                'reserved_usd':usd(totals['nano_usd'])}

    def verify(self, state, config, phase):
        expected = identity(state,config)
        grant = state.get('trial_grant', {})
        commit_sha, record = self.read('grant-' + str(integer(grant.get('sequence'), 1, 24, 'grant sequence')))
        require(commit_sha == grant.get('sha') and record['identity'] == expected, 'grant identity mismatch')
        require(record['phase'] == phase and record['round'] == state['round'] and record['attempt'] == state['attempt'], 'grant phase mismatch')
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            require(os.environ.get('AUTOSE_JOB_ID') == record['job_id'], 'paid job identity mismatch')
        claim_sha, claim = self.read('claim')
        require(claim_sha == state.get('trial_claim') and claim == {'kind':'claim','identity':expected}, 'claim identity mismatch')
        return record


def response_cost(body):
    """Conservative usage estimate, not an invoice. Missing detail is unknown spend."""
    require(body.get('model') == MODEL and body.get('service_tier') == 'default', 'returned model/tier unavailable or unsupported')
    u = body.get('usage')
    require(isinstance(u,dict), 'provider usage unavailable')
    i = integer(u.get('input_tokens'),0,INPUT_CEILING,'input usage')
    o = integer(u.get('output_tokens'),0,16000,'output usage')
    require(integer(u.get('total_tokens'),0,INPUT_CEILING+16000,'total usage') == i+o, 'inconsistent provider usage')
    details = u.get('input_tokens_details')
    require(isinstance(details,dict), 'input cost details unavailable')
    c = integer(details.get('cached_tokens'),0,i,'cached usage')
    w = integer(details.get('cache_write_tokens'),0,i,'cache-write usage')
    splits = details.get('cache_write_tokens_details')
    require(isinstance(splits,dict), 'cache-write lifetimes unavailable')
    w30 = integer(splits.get('ttl_30m_tokens'),0,w,'30m usage')
    w12 = integer(splits.get('ttl_12h_tokens'),0,w,'12h usage')
    require(w30+w12 == w and c+w <= i, 'inconsistent cache accounting')
    nano = (i-c-w)*RATES['ordinary'] + c*RATES['cached'] + w30*RATES['write_30m'] + w12*RATES['write_12h'] + o*RATES['output']
    return {'pricing':PRICING, 'currency':'USD', 'estimated_nano_usd':nano, 'estimated_usd':usd(nano),
            'basis':'Standard long-context + 10% uplift upper estimate; reasoning included in output',
            'ordinary_input_tokens':i-c-w, 'cached_tokens':c, 'write_30m_tokens':w30, 'write_12h_tokens':w12}
