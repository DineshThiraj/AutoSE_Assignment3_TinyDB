"""Controller-owned six-stage transitions, budgets and evidence."""
from __future__ import annotations

import copy
import time
from pathlib import Path

from . import contracts
from .broker import ask, live_preflight
from .common import PIN, REPOSITORY, SECRET_PATTERN, STAGES, digest, encoded, gate, invalidate, json_load, passed, require, sha
from .github import APIError
from .executor import execute
from .source import diff, replacements, snapshot, source_hash, tests_cover
from .trial import event_guard, issue_scope_hash
import os


def remaining(state):
    seconds = min(state['limits']['seconds'], 2400) - (time.time() - state['started_at'])
    require(seconds > 0, 'whole run time budget exhausted')
    return seconds


def admit(event, event_name, github, repository, *, run_id, run_attempt, config, fixture=False):
    require(not fixture or os.environ.get('GITHUB_ACTIONS') != 'true', 'fixture admission forbidden on hosted runner')
    if not fixture:
        live_preflight(config, require_key=False)
        event_guard(config,event,event_name,run_attempt)
    info = github.verify_repository()
    require(event.get('repository', {}).get('full_name') == REPOSITORY, 'wrong event repository')
    issue = event.get('issue') or {}
    require(type(issue.get('number')) is int and issue['number'] > 0 and 'pull_request' not in issue, 'issue event required; PR comments rejected')
    actor = event.get('sender') or {}
    require(actor.get('type') == 'User' and actor.get('login') and not actor['login'].endswith('[bot]'), 'bot/unknown actor')
    if event_name == 'issues':
        require(event.get('action') == 'labeled' and event.get('label', {}).get('name') == 'autose', 'label trigger mismatch')
    elif event_name == 'issue_comment':
        require(event.get('action') == 'created' and event.get('comment', {}).get('body') == '/autose', 'exact issue command required')
    else:
        require(False, 'unsupported trigger')
    permission = github.repo('GET', '/collaborators/' + actor['login'] + '/permission')
    require(permission.get('permission') in {'write', 'maintain', 'admin'}, 'actor lacks current repository write authority')
    require(info['default_branch'] == 'main' and info.get('has_issues') is True, 'protected main and Issues setup required')
    branch = github.repo('GET', '/branches/main')
    require(branch.get('protected') is True, 'main unprotected')
    try:
        protection = github.repo('GET', '/branches/main/protection')
    except APIError as error:
        require(error.status in {403,404}, 'protection lookup unavailable')
        protection = github.verify_rules_preflight(json_load(Path(repository)/'workflow/config/repository-preflight.json'))
    else:
        require(protection.get('enforce_admins', {}).get('enabled') is True, 'admin bypass must be disabled')
        reviews = protection.get('required_pull_request_reviews')
        require(isinstance(reviews, dict), 'required PR rule absent')
        require(not any(reviews.get('bypass_pull_request_allowances', {}).get(k) for k in ('users','teams','apps')), 'PR bypass present')
        require(protection.get('allow_force_pushes', {}).get('enabled') is False and protection.get('allow_deletions', {}).get('enabled') is False, 'force/deletion protection absent')
        checks = protection.get('required_status_checks') or {}
        require('tinydb-tests' in checks.get('contexts', []) or any(c.get('context') == 'tinydb-tests' for c in checks.get('checks', [])), 'required CI protection absent')
    current_issue = github.repo('GET', '/issues/' + str(issue['number']))
    require(current_issue['state'] == 'open' and 'pull_request' not in current_issue, 'issue not open')
    issue_data = {k:current_issue.get(k) or '' for k in ('number','title','body','html_url','updated_at')}
    require(isinstance(issue_data['body'], str) and 0 < len(issue_data['body'].encode()) < 40_000, 'empty/oversized issue')
    require(not SECRET_PATTERN.search(encoded(issue_data)), 'credential-like issue material; stop before provider input')
    require(str(run_id).isdigit() and int(run_attempt) > 0, 'invalid run identity')
    # A stable branch is the durable issue-to-PR index. Reconcile completed/replayed
    # events before model calls; unfamiliar existing work stops instead of duplicating.
    prs = github.issue_prs(issue['number'])
    require(not prs, 'existing issue PR: reconcile/resume saved attempt; no duplicate model run')
    if not fixture:
        require(issue_scope_hash(issue_data) == config['trial']['issue_hash'], 'approved issue changed')
    source = snapshot(repository)
    state = {
        'repository':REPOSITORY,'pin':PIN,'base_sha':sha(branch['commit']['sha']),
        'run_id':str(run_id),'run_attempt':int(run_attempt),'event_id':str(run_id),
        'trigger':{'kind':event_name,'actor':actor['login'],'comment_id':event.get('comment',{}).get('id')},
        'attempt_id':f'{run_id}-{run_attempt}','started_at':time.time(),
        'execution_kind':'local_fixture' if fixture else 'hosted',
        'issue':issue_data,'issue_hash':digest(encoded(issue_data)),
        'authorization':{'actor':actor['login'],'permission':permission['permission'],
            'scope':'Only the exact explicit frozen issue scope; inferred requirements are not approved.'},
        'protection_verification':protection,
        'limits':{'calls':config.get('trial',{}).get('max_calls',24),'tokens':config.get('token_budget') or 200_000,'seconds':2400},
        'usage':{'calls':0,'tokens':0,'unknown':False},'baseline':source,'source':copy.deepcopy(source),
        'round':1,'attempt':1,'route':'requirements','events':[],'gates':{},
    }
    gate(state, 'admission', 'passed', 'Authorized exact issue event; repository/protection/preflight verified.')
    return state


def requirements(state, broker, repo):
    result = ask(broker, state, 'requirements', repo)
    state['spec'] = result
    valid = contracts.specification(result, state['issue'])
    if not valid:
        gate(state, 'requirements', 'needs_clarification', 'Critical questions remain; authorized clarification required.')
        return
    assessment = ask(broker, state, 'requirements', repo, semantic_input={
        'stage':'requirements','issue':state['issue'],'authorization':state['authorization'],
        'artifact':result,'source':state['source']})
    contracts.semantic(assessment)
    state['requirements_validation'] = assessment
    gate(state, 'requirements', 'passed', 'A1 structure, explicit-scope ACs and fresh semantic validation passed.')


def design(state, broker, repo):
    passed(state, 'requirements')
    result = ask(broker, state, 'design', repo)
    contracts.design(result, state['spec'], state['source'])
    assessment = ask(broker, state, 'design', repo, semantic_input={
        'stage':'design','issue':state['issue'],'artifact':result,'specification':state['spec'],'source':state['source']})
    contracts.semantic(assessment)
    state['design'], state['design_validation'] = result, assessment
    gate(state, 'design', 'passed', 'Every criterion grounded in actual files/functions; five A2 constraints assessed.')


def implementation(state, broker, repo):
    passed(state, 'design')
    require(1 <= state['round'] <= 2 and 1 <= state['attempt'] <= 2, 'repair/review bound exhausted')
    result = ask(broker, state, 'implementation', repo)
    source = replacements(state['source'], result.get('files'), 'implementation', baseline=state['baseline'])
    planned = {t['path'] for t in state['design']['targets']}
    require(set(result['files']) <= planned, 'implementation edits outside validated design')
    require(diff(state['baseline'], source), 'no actual implementation diff')
    state['source'] = source
    state['patch'] = diff(state['baseline'], source)
    invalidate(state, 'implementation')


def compile_stage(state, directory, **execution_options):
    execution_options['timeout'] = min(execution_options.get('timeout',300),remaining(state),300)
    result = execute(state['source'], directory, phase='compile', **execution_options)
    state['execution'] = result
    gate(state, 'implementation', 'passed' if result['passed'] else 'failed',
         'Fixed compile execution completed.', source_hash=source_hash(state['source']))


def author_tests(state, broker, repo):
    passed(state, 'implementation')
    result = ask(broker, state, 'testing', repo)
    source = replacements(state['source'], result.get('files'), 'testing', baseline=state['baseline'])
    tests_cover(source, state['baseline'], result.get('test_map'), [c['id'] for c in state['spec']['criteria']])
    state['source'], state['test_map'] = source, result['test_map']
    state['patch'] = diff(state['baseline'], source)


def test_stage(state, directory, *, baseline_ids, **execution_options):
    passed(state, 'implementation')
    tests_cover(state['source'], state['baseline'], state['test_map'], [c['id'] for c in state['spec']['criteria']])
    execution_options['timeout'] = min(execution_options.get('timeout',300),remaining(state),300)
    result = execute(state['source'], directory, phase='testing', baseline_ids=baseline_ids,
                     test_map=state['test_map'], **execution_options)
    state['execution'] = result
    state['tested_source_hash'] = source_hash(state['source'])
    gate(state, 'testing', 'passed' if result['passed'] else 'failed',
         'Candidate pytest is diagnostic; independent verified baseline/generated verdict required.',
         source_hash=state['tested_source_hash'], case_count=result.get('case_count'))


def release(state, github):
    passed(state, 'testing')
    from .verification import require_authoritative
    require_authoritative(state.get('execution',{}),source_hash(state['source']))
    remaining(state)
    github.publish(state)
    wait_seconds = min(300, max(0, state['limits']['seconds'] - (time.time() - state['started_at'])))
    ci = github.wait_ci(state['publication'], seconds=wait_seconds) if hasattr(github, 'wait_ci') else github.ci(state['publication'])
    state['publication']['ci'] = ci
    gate(state, 'release', 'passed' if ci['status'] == 'passed' else 'pending',
         'PR open; exact-head CI ' + ci['status'], head_sha=state['publication']['head_sha'])


def independent_review(state, broker, repo, *, own_test_result=None):
    passed(state, 'release')
    require(1 <= state['round'] <= 2, 'no third review round')
    require(state['round'] == len(state.get('review_history', [])) + 1, 'review round already completed')
    if own_test_result is None:
        result = ask(broker, state, 'review', repo)
    else:
        from .broker import context
        inputs = context(state, 'review', repo)
        # The only extra input is the reviewer's own fixed execution result.
        inputs['own_test_result'] = own_test_result
        instruction = (Path(repo) / 'workflow/prompts/review.txt').read_text()
        result = broker.ask(state, 'review', instruction, inputs)
        require(result.get('run_tests') is False, 'review test request loop exhausted')
        require(own_test_result.get('passed') is True or result.get('verdict') == 'REQUEST_CHANGES', 'review cannot approve after its own tests failed')
    contracts.review(result, state['source'])
    state['review'] = result
    state['review_requested_tests'] = result['run_tests']


def publish_review(state, github):
    passed(state, 'release')
    remaining(state)
    require(not state.get('review_requested_tests'), 'review test request not resolved')
    require(state['round'] == len(state.get('review_history', [])) + 1, 'review round already posted')
    posted = github.post_review(state)
    state['posted_review'] = posted
    state.setdefault('review_history', []).append({'round':state['round'],'review':state['review'],'posted':posted})
    if state['review']['verdict'] == 'APPROVE':
        gate(state, 'review', 'passed' if posted['github_approved'] else 'pending',
             'Model approved; platform review event=' + posted['event'])
    elif state['round'] >= 2:
        gate(state, 'review', 'exhausted', 'Two total review rounds consumed; unapproved; human decision pending.')
    else:
        target = min((f['stage'] for f in state['review']['findings']), key=STAGES.index)
        state['feedback'] = state['review']['findings']
        state['next_route'] = target
        gate(state, 'review', 'failed', 'Changes requested; validated route=' + target)


def repair(state):
    require(state['gates'].get('review', {}).get('status') == 'failed' and state['round'] == 1, 'no further repair cycle permitted')
    state['round'], state['attempt'] = 2, 1
    invalidate(state, state['next_route'])


def retry(state):
    require(state['attempt'] == 1 and state['round'] <= 2, 'implementation retry exhausted')
    require(any(state['gates'].get(s, {}).get('status') == 'failed' for s in ('implementation','testing')), 'retry without failed execution gate')
    state['attempt'] = 2
    invalidate(state, 'implementation')
