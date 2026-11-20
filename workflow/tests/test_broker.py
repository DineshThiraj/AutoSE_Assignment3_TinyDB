import json
import time
import urllib.error

import pytest

from autose.broker import ResponsesBroker, live_preflight
from autose.common import GateError


from autose.trial import Ledger
from trial_fixtures import MemoryGitHub, config, prepare_state, FixtureConsumer


def broker_for(state,phase):
    prepare_state(state)
    cfg=config(state)
    ledger=Ledger(MemoryGitHub())
    ledger.claim(state,cfg)
    ledger.reserve(state,cfg,phase)
    return ResponsesBroker(cfg,ledger=ledger,phase=phase,consumer=FixtureConsumer(ledger,cfg))


def response(**changes):
    value={'model':'gpt-6.1-sol','service_tier':'default','status':'completed','id':'fixture-response','usage':{'input_tokens':9,'output_tokens':3,'total_tokens':12,'input_tokens_details':{'cached_tokens':0,'cache_write_tokens':0,'cache_write_tokens_details':{'ttl_30m_tokens':0,'ttl_12h_tokens':0}}},
        'output':[{'type':'message','content':[{'type':'output_text','text':'{"pass":true}'}]}]}
    value.update(changes);return value


def mock_http(monkeypatch,body=None,error=None):
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return json.dumps(body).encode()
    class Transport:
        def open(self,request,timeout):
            assert request.full_url=='https://api.openai.com/v1/responses'
            assert 'unit-test-only-placeholder' not in request.data.decode()
            if error:raise error
            return Reply()
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Transport())
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')


def test_adapter_usage_contract_without_any_network_call(state,monkeypatch):
    mock_http(monkeypatch,response())
    state['execution_kind']='hosted' # Transport remains the in-memory test double.
    assert broker_for(state,'requirements').ask(state,'requirements','JSON instruction',{'issue':'fixture'})=={'pass':True}
    assert {k:state['usage'][k] for k in ('calls','tokens','unknown')}=={'calls':1,'tokens':12,'unknown':False}
    assert state['usage']['estimated_nano_usd']==9*4400+3*16500
    assert state['calls'][0]['usage']['total_tokens']==12
    assert 'unit-test-only-placeholder' not in json.dumps(state)


def test_timeout_usage_unknown_no_implicit_retry(state,monkeypatch):
    mock_http(monkeypatch,error=urllib.error.URLError('unit-test-only-placeholder'))
    state['execution_kind']='hosted'
    broker=broker_for(state,'design')
    with pytest.raises(GateError,match='usage unknown') as raised:broker.ask(state,'design','JSON',{})
    assert 'unit-test-only-placeholder' not in str(raised.value)
    assert state['usage']['unknown'] is True and state['usage']['calls']==1
    with pytest.raises(GateError,match='unknown'):broker.ask(state,'design','JSON',{})


@pytest.mark.parametrize('body',[response(usage=None),response(output=[]),response(output=[{'type':'message','content':[{'type':'output_text','text':'not JSON'}]}])])
def test_provider_bad_output_is_not_success(state,monkeypatch,body):
    mock_http(monkeypatch,body)
    state['execution_kind']='hosted'
    with pytest.raises(GateError):broker_for(state,'review').ask(state,'review','JSON',{})


def test_incomplete_response_preserves_actual_usage(state,monkeypatch):
    mock_http(monkeypatch,response(status='incomplete'))
    state['execution_kind']='hosted'
    with pytest.raises(GateError,match='incomplete'):broker_for(state,'review').ask(state,'review','JSON',{})
    assert state['usage']['tokens']==12 and state['calls'][0]['usage']['total_tokens']==12


def test_phase_cannot_exceed_durable_reserved_calls(state,monkeypatch):
    mock_http(monkeypatch,response())
    broker=broker_for(state,'implementation')
    broker.ask(state,'implementation','JSON',{})
    with pytest.raises(GateError,match='phase calls exhausted'):
        broker.ask(state,'implementation','JSON',{})
    assert state['usage']['calls']==1


@pytest.mark.parametrize('bad', ['no_cache_details','wrong_model','wrong_tier','over_output'])
def test_unknown_cost_or_provider_contract_violation_holds_reservation(state,monkeypatch,bad):
    body=response()
    if bad=='no_cache_details':del body['usage']['input_tokens_details']
    if bad=='wrong_model':body['model']='unapproved-model'
    if bad=='wrong_tier':body['service_tier']='priority'
    if bad=='over_output':body['usage'].update(output_tokens=101,total_tokens=110)
    mock_http(monkeypatch,body)
    broker=broker_for(state,'requirements')
    grant=state['trial_grant'].copy()
    with pytest.raises(GateError):broker.ask(state,'requirements','JSON',{})
    assert state['usage']['unknown'] is True
    assert state['calls'][0]['actual_model']==body['model']
    assert state['calls'][0]['service_tier']==body['service_tier']
    assert state['calls'][0]['usage']==body['usage']
    with pytest.raises(GateError,match='unknown'):broker.ask(state,'requirements','JSON',{})
    with pytest.raises(GateError,match='unknown'):broker.ledger.reserve(state,broker.config,'design')
    assert state['trial_grant']==grant and state['usage']['calls']==1


def test_approval_expires_between_calls_without_second_http_request(state,monkeypatch):
    mock_http(monkeypatch,response())
    broker=broker_for(state,'requirements')
    broker.ask(state,'requirements','JSON',{})
    expiry=broker.config['trial']['expires_at']
    monkeypatch.setattr(time,'time',lambda:expiry+1)
    with pytest.raises(GateError,match='expired'):broker.ask(state,'requirements','JSON',{})
    assert state['usage']['calls']==1


def test_missing_actual_repository_secret_stops_without_http(state,monkeypatch):
    prepare_state(state);cfg=config(state)
    monkeypatch.delenv('AUTOSE_MODEL_API_KEY',raising=False)
    with pytest.raises(GateError,match='secret not supplied'):ResponsesBroker(cfg,phase='requirements')


@pytest.mark.parametrize('key,value',[('enabled',False),('paid_authorized',False),('provider_cap_verified',False),
    ('hard_cap_evidence',None),('provider_support_evidence',None),('model',None),('authorization_expires_at',0)])
def test_paid_prerequisites_each_required(state,monkeypatch,key,value):
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    prepare_state(state);cfg=config(state);cfg[key]=value
    with pytest.raises(GateError):live_preflight(cfg)
