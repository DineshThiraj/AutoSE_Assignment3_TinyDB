import json
import time
import urllib.error

import pytest

from autose.broker import ResponsesBroker, live_preflight
from autose.common import GateError


def config():return {'enabled':True,'adapter':'openai-responses','model':'fixture-not-a-real-model','effort':'medium',
    'token_budget':200000,'max_output_tokens':100,'provider_support_evidence':'fixture only',
    'hard_cap_evidence':'fixture only','provider_cap_verified':True,'paid_authorized':True,
    'paid_authorization_evidence':'fixture only; no real authorization','authorization_expires_at':time.time()+100}


def response(**changes):
    value={'status':'completed','id':'fixture-response','usage':{'input_tokens':9,'output_tokens':3,'total_tokens':12},
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
    assert ResponsesBroker(config()).ask(state,'requirements','JSON instruction',{'issue':'fixture'})=={'pass':True}
    assert state['usage']=={'calls':1,'tokens':12,'unknown':False}
    assert state['calls'][0]['usage']['total_tokens']==12
    assert 'unit-test-only-placeholder' not in json.dumps(state)


def test_timeout_usage_unknown_no_implicit_retry(state,monkeypatch):
    mock_http(monkeypatch,error=urllib.error.URLError('unit-test-only-placeholder'))
    state['execution_kind']='hosted'
    broker=ResponsesBroker(config())
    with pytest.raises(GateError,match='usage unknown') as raised:broker.ask(state,'design','JSON',{})
    assert 'unit-test-only-placeholder' not in str(raised.value)
    assert state['usage']['unknown'] is True and state['usage']['calls']==1
    with pytest.raises(GateError,match='usage unknown'):broker.ask(state,'design','JSON',{})


@pytest.mark.parametrize('body',[response(usage=None),response(output=[]),response(output=[{'type':'message','content':[{'type':'output_text','text':'not JSON'}]}])])
def test_provider_bad_output_is_not_success(state,monkeypatch,body):
    mock_http(monkeypatch,body)
    state['execution_kind']='hosted'
    with pytest.raises(GateError):ResponsesBroker(config()).ask(state,'review','JSON',{})


def test_incomplete_response_preserves_actual_usage(state,monkeypatch):
    mock_http(monkeypatch,response(status='incomplete'))
    state['execution_kind']='hosted'
    with pytest.raises(GateError,match='incomplete'):ResponsesBroker(config()).ask(state,'review','JSON',{})
    assert state['usage']['tokens']==12 and state['calls'][0]['usage']['total_tokens']==12


@pytest.mark.parametrize('key,value',[('enabled',False),('paid_authorized',False),('provider_cap_verified',False),
    ('hard_cap_evidence',None),('provider_support_evidence',None),('model',None),('authorization_expires_at',0)])
def test_paid_prerequisites_each_required(monkeypatch,key,value):
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    cfg=config();cfg[key]=value
    with pytest.raises(GateError):live_preflight(cfg)
