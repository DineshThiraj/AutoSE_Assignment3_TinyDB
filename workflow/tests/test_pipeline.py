import copy
import json
from pathlib import Path
import time

import pytest

from autose import contracts, engine
from autose.broker import context, live_preflight
from autose.common import GateError, STAGES, artifact, budget, gate, invalidate, load_artifact, readiness
from autose.executor import execute, junit
from autose.source import allowed, replacements, source_hash, tests_cover as check_test_coverage
from conftest import FixtureBroker, FixturePublisher, REPO, PYTHON, TESTS, plan, specification


def run_attempt(state,broker,tmp_path,baseline_ids):
    prefix=f"r{state['round']}a{state['attempt']}"
    engine.implementation(state,broker,REPO)
    engine.compile_stage(state,tmp_path/(prefix+'-build'),local_fixture=True,python=PYTHON)
    assert state['gates']['implementation']['status']=='passed'
    engine.author_tests(state,broker,REPO)
    engine.test_stage(state,tmp_path/(prefix+'-test'),baseline_ids=baseline_ids,local_fixture=True,python=PYTHON)


def test_actual_tinydb_retry_and_six_stage_contract(state,tmp_path,baseline_ids):
    broker=FixtureBroker(broken_first=True)
    engine.requirements(state,broker,REPO)
    engine.design(state,broker,REPO)
    run_attempt(state,broker,tmp_path,baseline_ids)
    assert state['gates']['testing']['status']=='failed' # Genuine pinned-source regression fails.
    assert 'KeyError' in state['execution']['log']
    engine.retry(state)
    run_attempt(state,broker,tmp_path,baseline_ids)
    assert state['gates']['testing']['status']=='passed'
    assert state['execution']['case_count']==232 # 228 original + 4 parameterized new cases.
    assert source_hash(state['source'])==state['tested_source_hash']
    publisher=FixturePublisher()
    engine.release(state,publisher)
    engine.independent_review(state,broker,REPO)
    reviewer_context=[c for r,c in broker.requests if r=='review'][0]
    assert set(reviewer_context)=={'issue','diff','source'}
    assert 'specification' not in reviewer_context and 'A1_skill' not in reviewer_context
    engine.publish_review(state,publisher)
    assert {c['role'] for c in state['calls']} == {'requirements','design','implement_test','review'}
    assert all(state['gates'][s]['status']=='passed' for s in STAGES)
    check=readiness(state)
    assert check['execution_kind']=='local_fixture' and check['automated_gates_satisfied'] is False
    assert check['merge_authorized'] is False and check['human_decision']=='pending'
    from autose.cli import render
    artifact(tmp_path/'artifacts',state,render(state))
    assert all((tmp_path/'artifacts'/p).is_file() for p in ('spec.md','design.md','diff.patch','test_report.md','pr.md','review.md','junit.xml'))
    assert load_artifact(tmp_path/'artifacts')['tested_source_hash']==state['tested_source_hash']


def test_vague_issue_stops_with_real_draft_artifacts(state,tmp_path):
    broker=FixtureBroker(vague=True)
    engine.requirements(state,broker,REPO)
    assert state['gates']['requirements']['status']=='needs_clarification'
    assert state['spec']['questions'] and len(broker.requests)==1
    with pytest.raises(GateError,match='requirements gate'):
        engine.design(state,broker,REPO)
    from autose.cli import render
    outputs=render(state)
    assert all(p in outputs for p in ('spec.md','requirements_spec.md','assumptions_questions.md','validation_summary.md'))


def test_real_compiler_error_is_not_model_success(state,tmp_path):
    state['source']['tinydb/table.py']='def broken(:\n'
    engine.compile_stage(state,tmp_path/'bad-compile',local_fixture=True,python=PYTHON)
    assert state['gates']['implementation']['status']=='failed'
    assert 'SyntaxError' in state['execution']['log']


def test_two_review_rounds_exhaust_and_route(state):
    broker=FixtureBroker(reject_first=True)
    for s in STAGES[:5]:gate(state,s,'passed','fixture gate')
    state['patch']='fixture diff'
    state['publication']={'head_sha':'b'*40}
    engine.independent_review(state,broker,REPO)
    engine.publish_review(state,FixturePublisher())
    assert state['next_route']=='design'
    engine.repair(state)
    assert state['round']==2 and state['route']=='design'
    assert state['gates']['requirements']['status']=='passed'
    assert all(s not in state['gates'] for s in STAGES[1:])
    for s in STAGES[1:5]:gate(state,s,'passed','fixture gate')
    state['review']={'verdict':'REQUEST_CHANGES','summary':'fixture','run_tests':False,'findings':[
        {'path':'tinydb/table.py','line':1,'stage':'implementation','evidence':'fixture'}]}
    state['review_requested_tests']=False
    engine.publish_review(state,FixturePublisher())
    assert state['gates']['review']['status']=='exhausted'
    with pytest.raises(GateError):engine.repair(state)
    with pytest.raises(GateError):engine.independent_review(state,broker,REPO)
    assert readiness(state)['automated_gates_satisfied'] is False


@pytest.mark.parametrize('target',STAGES[:4])
def test_every_review_route_invalidates_downstream_only(state,target):
    for s in STAGES:gate(state,s,'passed','fixture')
    invalidate(state,target)
    assert set(state['gates'])==set(STAGES[:STAGES.index(target)])


@pytest.mark.parametrize('path',['../tinydb/x.py','tinydb/../tests/x.py','/tinydb/x.py','tinydb//x.py',
    'tinydb\\x.py','.github/workflows/autose.yml','workflow/autose/cli.py','tinydb/.git/config','tinydb/x.py\x00'])
def test_patch_injection_denied(path):
    with pytest.raises(GateError):allowed(path,'implementation')


def test_original_test_edit_and_unmapped_assertions_denied(state):
    with pytest.raises(GateError):replacements(state['source'],{'tests/test_tables.py':'assert True'},'testing',baseline=state['baseline'])
    with pytest.raises(GateError):check_test_coverage({'tests/test_autose_x.py':'def test_x():\n    pass\n'},state['baseline'],
        {'AC-001':'tests/test_autose_x.py::test_x'},['AC-001'])
    with pytest.raises(GateError):check_test_coverage(state['source'],state['baseline'],{},['AC-001'])
    with pytest.raises(GateError,match='credential-like'):
        replacements(state['source'],{'tinydb/table.py':'token = "ghp_'+'a'*36+'"'},'implementation',baseline=state['baseline'])


def test_artifact_tamper_and_replay_are_not_silent(state,tmp_path):
    root=tmp_path/'a'
    artifact(root,state,{'spec.md':'fixture'})
    with pytest.raises(GateError):artifact(root,state)
    (root/'spec.md').write_text('changed')
    with pytest.raises(GateError,match='hash'):load_artifact(root)


@pytest.mark.parametrize('change',[{'calls':24},{'tokens':200001},{'unknown':True}])
def test_global_budget_failures_stop(state,change):
    state['usage'].update(change)
    with pytest.raises(GateError):budget(state)


def test_timeout_budget_and_retry_ceiling(state):
    state['started_at']=time.time()-2401
    with pytest.raises(GateError):budget(state)
    state['attempt']=2
    with pytest.raises(GateError):engine.retry(state)
    state['round']=3
    with pytest.raises(GateError):engine.independent_review(state,FixtureBroker(),REPO)


def test_provider_disabled_and_fixture_context_independent(state):
    with pytest.raises(GateError,match='deferred'):live_preflight({'enabled':False})
    state['spec']={'SECRET_IMPLEMENTER_TRACE':'do not reveal'}
    state['patch']='diff'
    review=context(state,'review',REPO)
    assert set(review)=={'issue','diff','source'}
    assert 'SECRET_IMPLEMENTER_TRACE' not in json.dumps(review)


def test_spec_rejects_unapproved_inferred_and_fabricated_quote(state):
    spec=specification(state)
    assert contracts.specification(spec,state['issue']) is True
    for field,value in [('approval','PROPOSED'),('evidence','INFERRED'),('source_quote','fabricated scope')]:
        changed=copy.deepcopy(spec)
        changed['criteria'][0][field]=value
        with pytest.raises(GateError):contracts.specification(changed,state['issue'])


def test_design_missing_constraint_and_invented_function_stop(state):
    state['spec']=specification(state)
    for key,value in [('constraints',{}),('targets',[{'path':'tinydb/table.py','function':'not_real'}])]:
        changed=plan();changed[key]=value
        with pytest.raises(GateError):contracts.design(changed,state['spec'],state['source'])


@pytest.mark.parametrize('xml',['<testsuites><testsuite tests="0"/></testsuites>',
    '<testsuites><testsuite errors="1"><testcase classname="tests.x" name="test_x"/></testsuite></testsuites>',
    '<testsuite><testcase name="test_x"><skipped/></testcase></testsuite>'])
def test_empty_skipped_or_error_junit_cannot_pass(tmp_path,xml):
    p=tmp_path/'junit.xml';p.write_text(xml)
    with pytest.raises(GateError):junit(p)
