import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading
import time

import pytest

from autose import engine
from autose.broker import ResponsesBroker, live_preflight
from autose.common import GateError, REPOSITORY
from autose.github import APIError
from autose.trial import Ledger, event_guard, response_cost, approval_scope_hash
from trial_fixtures import MemoryGitHub, config, prepare_state, FixtureConsumer


@pytest.fixture
def trial(state,monkeypatch):
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:pytest.fail('Network forbidden in D6 negative tests'))
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    prepare_state(state)
    return state, config(state), MemoryGitHub()


def trigger():
    return {'repository':{'full_name':REPOSITORY},'issue':{'number':3},'sender':{'type':'User','login':'DineshThiraj'},
            'action':'created','comment':{'id':123,'body':'/autose','user':{'login':'DineshThiraj'},
            'created_at':datetime.now(timezone.utc).isoformat()}}


@pytest.mark.parametrize('change', ['issue','actor','body','label','pr','old_comment','bot','edited','other_repository'])
def test_unauthorized_events_stop_before_github_or_model(trial,change):
    from conftest import REPO
    s,c,g = trial
    e = trigger()
    event_name = 'issue_comment'
    if change == 'issue':e['issue']['number']=4
    if change == 'actor':e['sender']['login']='stranger'
    if change == 'body':e['comment']['body']='/autose now'
    if change == 'label':event_name='issues';e.update(action='labeled',label={'name':'autose'})
    if change == 'pr':e['issue']['pull_request']={}
    if change == 'old_comment':e['comment']['created_at']='2020-01-01T00:00:00Z'
    if change == 'bot':e['sender']['type']='Bot'
    if change == 'edited':e['action']='edited'
    if change == 'other_repository':e['repository']['full_name']='other/repo'
    with pytest.raises(GateError):
        event_guard(c,e,event_name,1)


def test_exact_authorized_trigger_and_reject_changed_issue(trial):
    s,c,g = trial
    event_guard(c,trigger(),'issue_comment',1)
    s['issue']['body'] += 'changed after approval'
    with pytest.raises(GateError,match='changed'):Ledger(g).claim(s,c)
    assert not g.refs


def test_valid_hosted_admission_is_narrow_and_does_not_call_provider(trial):
    from conftest import REPO
    from test_github import FakeAPI
    from autose.github import GitHub
    s,c,g = trial
    api=FakeAPI(s['baseline'])
    issue={**s['issue'],'html_url':'fixture://issue/3','updated_at':'fixture','state':'open'}
    from autose.trial import issue_scope_hash
    c['trial']['issue_hash']=issue_scope_hash(issue)
    c['trial']['approval']['scope_sha256']=approval_scope_hash(c)
    def transport(method,path,body):
        if path=='/repos/'+REPOSITORY+'/issues/3':return issue
        return api(method,path,body)
    admitted=engine.admit(trigger(),'issue_comment',GitHub(transport=transport),REPO,run_id='1',run_attempt=1,config=c)
    assert admitted['issue']['number']==3 and admitted['usage']['calls']==0
    assert admitted['trigger']['comment_id']==123
    issue['body']+=' Unexpected issue edit after paid approval.'
    with pytest.raises(GateError,match='approved issue changed'):
        engine.admit(trigger(),'issue_comment',GitHub(transport=transport),REPO,run_id='1',run_attempt=1,config=c)


def test_duplicate_trigger_and_new_approval_cannot_reopen_trial(trial):
    s,c,g = trial
    Ledger(g).claim(s,c)
    later = copy.deepcopy(s);later['run_id']='2'
    with pytest.raises(APIError):Ledger(g).claim(later,c)
    c['trial']['id']='a-different-approval'
    c['trial']['approval']['scope_sha256']=approval_scope_hash(c)
    with pytest.raises(APIError):Ledger(g).claim(later,c)
    with pytest.raises(GateError,match='another run/config'):Ledger(g).reserve(later,c,'requirements')
    assert len(g.refs)==1


@pytest.mark.parametrize('where',['admission','claim','reserve','broker'])
def test_workflow_rerun_never_reaches_model(trial,monkeypatch,where):
    s,c,g = trial
    ledger = Ledger(g)
    ledger.claim(s,c);ledger.reserve(s,c,'requirements')
    original = copy.deepcopy(g.refs)
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    if where=='admission':
        with pytest.raises(GateError,match='reruns'):event_guard(c,trigger(),'issue_comment',2)
    elif where=='claim':
        with pytest.raises(GateError,match='reruns'):Ledger(g).claim(s,c)
    elif where=='reserve':
        with pytest.raises(GateError,match='reruns'):Ledger(g).reserve(s,c,'requirements')
    else:
        with pytest.raises(GateError,match='reruns'):ResponsesBroker(c,ledger=Ledger(g),phase='requirements').ask(s,'requirements','JSON',{})
    assert g.refs==original


def test_concurrent_claim_has_exactly_one_winner(trial):
    s,c,g = trial
    barrier = threading.Barrier(2)
    g.before_ref = lambda:barrier.wait(timeout=5)
    def claim(run):
        candidate=copy.deepcopy(s);candidate['run_id']=str(run)
        try:Ledger(g).claim(candidate,c);return candidate
        except APIError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(claim,(1,2)))
    winner=[x for x in results if x]
    assert len(winner)==1 and len(g.refs)==1
    g.before_ref=None
    Ledger(g).reserve(winner[0],c,'requirements')


def test_concurrent_reservation_and_stale_checkpoint_are_fail_closed(trial):
    s,c,g=trial
    Ledger(g).claim(s,c)
    old=copy.deepcopy(s)
    barrier=threading.Barrier(2)
    g.before_ref=lambda:barrier.wait(timeout=5)
    def reserve(_):
        candidate=copy.deepcopy(s)
        try:Ledger(g).reserve(candidate,c,'requirements');return candidate
        except APIError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(reserve,(1,2)))
    assert len([x for x in results if x])==1
    g.before_ref=None
    with pytest.raises(APIError):Ledger(g).reserve(old,c,'requirements')
    assert len(g.refs)==2
    assert all(m in {'GET','POST'} for m,p,b in g.calls)


@pytest.mark.parametrize('dimension',['calls','tokens','usd'])
def test_durable_exhausted_budget_before_reservation_or_model(trial,dimension):
    s,c,g=trial
    if dimension=='calls':c['trial']['max_calls']=1
    if dimension=='tokens':c['trial']['max_tokens']=c['token_budget']=100
    if dimension=='usd':
        c['trial']['max_usd']=c['trial']['hard_cap']['limit_usd']=c['trial']['hard_cap']['remaining_usd']='0.01'
    c['trial']['approval']['scope_sha256']=approval_scope_hash(c)
    ledger=Ledger(g);ledger.claim(s,c)
    with pytest.raises(GateError,match='budget exhausted'):ledger.reserve(s,c,'requirements')
    assert len(g.refs)==1


def test_unspent_grants_are_burned_across_new_controller_instances(trial):
    s,c,g=trial
    c['trial']['max_calls']=2
    c['trial']['approval']['scope_sha256']=approval_scope_hash(c)
    Ledger(g).claim(s,c)
    Ledger(g).reserve(s,c,'requirements')
    # No actual provider call. Reconstructed clients cannot refund this reservation.
    with pytest.raises(GateError,match='call budget exhausted'):Ledger(g).reserve(s,c,'design')
    assert s['usage']['calls']==0


def test_duplicate_phase_extra_round_or_attempt_cannot_obtain_more_calls(trial):
    s,c,g=trial
    Ledger(g).claim(s,c);Ledger(g).reserve(s,c,'requirements')
    with pytest.raises(GateError,match='already reserved'):Ledger(g).reserve(s,c,'requirements')
    for key in ('round','attempt'):
        bad=copy.deepcopy(s);bad[key]=3
        with pytest.raises(GateError):Ledger(g).reserve(bad,c,'design')
    assert len(g.refs)==2


@pytest.mark.parametrize('defect',['expired','unavailable','support_project','no_cap','secret','pricing','approval','float_usd','nan_expiry'])
def test_missing_account_or_paid_evidence_blocks_before_model(trial,defect):
    s,c,g=trial
    t=c['trial']
    if defect=='expired':t['expires_at']=c['authorization_expires_at']=0
    if defect=='unavailable':t['provider_support']['available']=False
    if defect=='support_project':t['provider_support']['project_id']='wrong-project'
    if defect=='no_cap':t['hard_cap']['enforced']=False
    if defect=='secret':t['secret']['available']=False
    if defect=='pricing':t['pricing']['schedule']='unknown'
    if defect=='approval':t['approval']['verified']=False
    if defect=='float_usd':t['max_usd']=100.0
    if defect=='nan_expiry':t['expires_at']=c['authorization_expires_at']=float('nan')
    with pytest.raises(GateError):live_preflight(c)
    assert not g.refs


def test_paid_approval_does_not_cover_silent_scope_or_output_changes(trial):
    s,c,g=trial
    c['max_output_tokens']=101
    with pytest.raises(GateError,match='scope mismatch'):Ledger(g).claim(s,c)
    assert not g.refs


def cost_response():
    return {'model':'gpt-6.1-sol','service_tier':'default','usage':{'input_tokens':100,'output_tokens':10,'total_tokens':110,
        'input_tokens_details':{'cached_tokens':20,'cache_write_tokens':50,
        'cache_write_tokens_details':{'ttl_30m_tokens':30,'ttl_12h_tokens':20}},
        'output_tokens_details':{'reasoning_tokens':8}}}


def test_cost_covers_cache_lifetimes_long_context_and_uplift_without_double_count():
    result=response_cost(cost_response())
    assert result['estimated_nano_usd']==30*4400+20*220+30*5500+20*11000+10*16500
    assert result['estimated_usd']=='0.000686400'


@pytest.mark.parametrize('field',['model','service_tier','usage','input_tokens','output_tokens','total_tokens','cached_tokens','cache_write_tokens','cache_write_tokens_details','ttl_30m_tokens','ttl_12h_tokens'])
def test_missing_essential_cost_field_is_never_zero(field):
    body=cost_response()
    if field in body:del body[field]
    elif field in body['usage']:del body['usage'][field]
    elif field in body['usage']['input_tokens_details']:del body['usage']['input_tokens_details'][field]
    else:del body['usage']['input_tokens_details']['cache_write_tokens_details'][field]
    with pytest.raises(GateError):response_cost(body)


def test_ref_write_response_loss_burns_trial(trial):
    s,c,g=trial
    class LostReply:
        def repo(self,method,path,body=None):
            result=g.repo(method,path,body)
            if method=='POST' and path=='/git/refs':raise APIError('network')
            return result
    with pytest.raises(APIError):Ledger(LostReply()).claim(s,c)
    assert 'trial_claim' not in s
    with pytest.raises(APIError):Ledger(g).claim(s,c)
    assert len(g.refs)==1


def test_comment_timestamp_change_does_not_change_approved_scope(trial):
    from autose.common import digest, encoded
    s,c,g=trial
    s['issue']['updated_at']='comment changed metadata only'
    s['issue_hash']=digest(encoded(s['issue']))
    Ledger(g).claim(s,c)
    assert len(g.refs)==1


def test_remote_ledger_unavailable_or_no_grant_fails_before_model(trial):
    s,c,g=trial
    broker=ResponsesBroker(c,ledger=Ledger(g),phase='requirements')
    with pytest.raises(GateError):broker.ask(s,'requirements','JSON',{})
    assert s['usage']['calls']==0


def test_budgeted_protocol_slice_executes_real_source_without_network(state,monkeypatch,tmp_path,baseline_ids):
    """Seven fake Responses requests, five real reservations, actual 232-case suite.

    The HTTP responses and publisher/CI/review are doubles, never hosted evidence.
    """
    import json
    from conftest import FixtureBroker, FixturePublisher, REPO, PYTHON
    from autose.common import artifact, load_artifact, readiness
    from autose.cli import render
    prepare_state(state)
    c=config(state);g=MemoryGitHub()
    Ledger(g).claim(state,c)
    fixture=FixtureBroker()
    requests=[]
    active={}
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return active['reply']
    class Transport:
        def open(self,request,timeout):
            payload=json.loads(request.data)
            assert request.full_url=='https://api.openai.com/v1/responses'
            assert request.get_header('Openai-project')==c['trial']['project_id']
            assert payload['service_tier']=='default' and payload['store'] is False
            assert 'tools' not in payload and 'previous_response_id' not in payload
            context=json.loads(payload['input'][0]['content'][0]['text'])
            if active['phase']=='review':assert set(context)=={'issue','diff','source'}
            snapshot=copy.deepcopy(state);snapshot['usage']['unknown']=False
            role={'author-tests':'testing'}.get(active['phase'],active['phase'])
            value=fixture.ask(snapshot,role,payload['instructions'],context)
            body=cost_response();body.update(status='completed',id='fixture-response-'+str(len(requests)),
                output=[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}])
            active['reply']=json.dumps(body).encode();requests.append(payload)
            return Reply()
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:Transport())
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    def broker(phase):
        # Pass through the same immutable artifact boundary as separate jobs.
        directory=tmp_path/('checkpoint-'+phase)
        artifact(directory,state)
        restored=load_artifact(directory);state.clear();state.update(restored)
        Ledger(g).reserve(state,c,phase)
        active['phase']=phase
        return ResponsesBroker(c,ledger=Ledger(g),phase=phase,consumer=FixtureConsumer(Ledger(g),c))
    engine.requirements(state,broker('requirements'),REPO)
    engine.design(state,broker('design'),REPO)
    engine.implementation(state,broker('implementation'),REPO)
    engine.compile_stage(state,tmp_path/'build',local_fixture=True,python=PYTHON)
    engine.author_tests(state,broker('author-tests'),REPO)
    from conftest import FixtureVerifier
    from autose.source import source_hash
    state['candidate_commit']={'head_sha':'b'*40,'source_sha256':source_hash(state['source'])}
    engine.test_stage(state,tmp_path/'tests',baseline_ids=baseline_ids,local_fixture=True,python=PYTHON,verifier=FixtureVerifier())
    assert state['execution']['passed'] and state['execution']['case_count']==232
    publisher=FixturePublisher();engine.release(state,publisher)
    engine.independent_review(state,broker('review'),REPO)
    engine.publish_review(state,publisher)
    assert len(requests)==state['usage']['calls']==7 and len(g.refs)==13
    assert state['usage']['tokens']==770 and state['usage']['estimated_usd']=='0.004804800'
    assert all(call['actual_model']=='gpt-6.1-sol' and call['service_tier']=='default' for call in state['calls'])
    assert readiness(state)['merge_authorized'] is False
    # Test-only hosted state must never escape as a genuine hosted evidence claim.
    state['execution_kind']='local_fixture'
    artifact(tmp_path/'final-fixture-evidence',state,render(state))
    assert readiness(state)['automated_gates_satisfied'] is False
