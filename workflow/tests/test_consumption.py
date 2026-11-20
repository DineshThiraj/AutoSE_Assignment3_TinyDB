"""Per-call consumption regressions against independent workers and shared ledger."""
import copy
from concurrent.futures import ThreadPoolExecutor
import io
import json
import threading
import time
import urllib.error

import pytest

from autose.broker import ResponsesBroker
from autose.common import GateError, digest
from autose.consumption import CallConsumer, ConsumptionAuthority, call_request, slot_name
from autose.consume_service import handler
from autose.github import APIError
from autose.trial import INPUT_CEILING, Ledger, PREFIX, approval_scope_hash
from trial_fixtures import FixtureConsumer, MemoryGitHub, config, prepare_state
from test_broker import response


@pytest.fixture
def reserved(state,monkeypatch):
    prepare_state(state);cfg=config(state)
    cfg['trial']['max_calls']=state['limits']['calls']=1
    cfg['trial']['max_tokens']=cfg['token_budget']=state['limits']['tokens']=INPUT_CEILING+100
    cfg['trial']['max_usd']=cfg['trial']['hard_cap']['limit_usd']=cfg['trial']['hard_cap']['remaining_usd']='12'
    cfg['trial']['approval']['scope_sha256']=approval_scope_hash(cfg)
    github=MemoryGitHub();ledger=Ledger(github)
    ledger.claim(state,cfg);ledger.reserve(state,cfg,'implementation')
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    return state,cfg,github


def transport(monkeypatch,calls,*,error=False):
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return json.dumps(response()).encode()
    class Transport:
        def open(self,request,timeout):
            assert request.full_url=='https://api.openai.com/v1/responses'
            calls.append(request)
            if error:raise urllib.error.URLError('fixture only')
            return Reply()
    monkeypatch.setattr('urllib.request.build_opener',lambda *args:Transport())


def worker(state,cfg,github):
    ledger=Ledger(github)
    return ResponsesBroker(cfg,ledger=ledger,phase='implementation',consumer=FixtureConsumer(ledger,cfg))


def test_concurrent_copies_of_one_grant_allow_only_one_model_request(reserved,monkeypatch):
    state,cfg,github=reserved
    requests=[];transport(monkeypatch,requests)
    barrier=threading.Barrier(3)
    github.before_ref=lambda:barrier.wait(timeout=5)
    def run(_):
        own=copy.deepcopy(state)
        try:
            value=worker(own,cfg,github).ask(own,'implementation','JSON',{'same':'checkpoint'})
            return 'accepted',own,value
        except APIError:return 'denied',own,None
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(run,range(3)))
    assert [r[0] for r in results].count('accepted')==1
    assert len(requests)==1 and sum(r[1]['usage']['calls'] for r in results)==1
    assert len([ref for ref in github.refs if PREFIX+'consume-' in ref])==1
    _,record=Ledger(github).read('consume-1-1')
    assert record['request']['request_sha256']==digest(requests[0].data)
    assert record['request']['job_id']=='implementation'
    assert record['request']['identity']['run_attempt']==1


def test_timeout_then_original_checkpoint_stays_consumed(reserved,monkeypatch):
    state,cfg,github=reserved
    checkpoint=copy.deepcopy(state)
    requests=[];transport(monkeypatch,requests,error=True)
    with pytest.raises(GateError,match='usage unknown'):
        worker(state,cfg,github).ask(state,'implementation','JSON',{})
    assert state['usage']['unknown'] is True and len(requests)==1
    with pytest.raises(APIError):
        worker(checkpoint,cfg,github).ask(checkpoint,'implementation','JSON',{})
    assert len(requests)==1 and checkpoint['usage']['calls']==0


def test_lost_consumption_reply_never_retries_or_calls_provider(reserved,monkeypatch):
    state,cfg,github=reserved
    requests=[];transport(monkeypatch,requests)
    class LostReply(FixtureConsumer):
        def consume(self,request):
            super().consume(request)
            raise GateError('consumption response unavailable')
    checkpoint=copy.deepcopy(state)
    broker=ResponsesBroker(cfg,ledger=Ledger(github),phase='implementation',consumer=LostReply(Ledger(github),cfg))
    with pytest.raises(GateError):broker.ask(state,'implementation','JSON',{})
    with pytest.raises(APIError):worker(checkpoint,cfg,github).ask(checkpoint,'implementation','JSON',{})
    assert requests==[] and len(github.refs)==3


@pytest.mark.parametrize('field,value',[('job_id','another-job'),('phase','review'),('call_index',2),('sequence',2),
                                      ('grant_sha','f'*40),('request_sha256','invalid'),('run_id','2'),('run_attempt',2)])
def test_consumption_request_is_bound_to_job_phase_slot_and_request(reserved,field,value):
    state,cfg,github=reserved
    ledger=Ledger(github);grant=ledger.verify(state,cfg,'implementation')
    request=call_request(state,grant,'implementation',1,'c'*64)
    if field in ('run_id','run_attempt'):request['identity'][field]=value
    else:request[field]=value
    with pytest.raises(GateError):ConsumptionAuthority(ledger,cfg).consume(request)
    assert len(github.refs)==2


def test_different_request_hash_does_not_reopen_used_call_slot(reserved):
    state,cfg,github=reserved
    ledger=Ledger(github);grant=ledger.verify(state,cfg,'implementation')
    request=call_request(state,grant,'implementation',1,'c'*64)
    ConsumptionAuthority(ledger,cfg).consume(request)
    request['request_sha256']='d'*64
    with pytest.raises(APIError):ConsumptionAuthority(Ledger(github),cfg).consume(request)
    assert len(github.refs)==3


def test_service_reply_without_durable_record_is_rejected(reserved,monkeypatch):
    state,cfg,github=reserved
    ledger=Ledger(github);grant=ledger.verify(state,cfg,'implementation')
    request=call_request(state,grant,'implementation',1,'c'*64)
    monkeypatch.setattr('autose.consumption.post_json',lambda *a,**k:{'receipt_sha':'f'*40})
    with pytest.raises(APIError):CallConsumer(cfg,ledger).consume(request)
    assert len(github.refs)==2


def test_client_verifies_remote_receipt_and_fails_closed_on_service_outage(reserved,monkeypatch):
    state,cfg,github=reserved
    ledger=Ledger(github);grant=ledger.verify(state,cfg,'implementation')
    request=call_request(state,grant,'implementation',1,'c'*64)
    authority=ConsumptionAuthority(ledger,cfg)
    monkeypatch.setattr('autose.consumption.post_json',lambda url,value,token,**k:authority.consume(value))
    receipt=CallConsumer(cfg,ledger).consume(request)
    assert receipt['slot']=='consume-1-1'
    with pytest.raises(APIError):CallConsumer(cfg,ledger).consume(request)
    def unavailable(*a,**k):raise GateError('service unavailable')
    monkeypatch.setattr('autose.consumption.post_json',unavailable)
    with pytest.raises(GateError):CallConsumer(cfg,ledger).consume(request)
    assert len(github.refs)==3


def test_stale_success_reply_is_not_authority_for_a_fresh_invocation(reserved,monkeypatch):
    state,cfg,github=reserved
    ledger=Ledger(github);grant=ledger.verify(state,cfg,'implementation')
    first=call_request(state,grant,'implementation',1,'c'*64)
    receipt=ConsumptionAuthority(ledger,cfg).consume(first)
    second=call_request(state,grant,'implementation',1,'c'*64)
    assert first['consumer_nonce']!=second['consumer_nonce']
    monkeypatch.setattr('autose.consumption.post_json',lambda *a,**k:receipt)
    with pytest.raises(GateError,match='receipt mismatch'):CallConsumer(cfg,ledger).consume(second)
    assert len(github.refs)==3


@pytest.mark.parametrize('auth,path',[('', '/v1/consume'),('Bearer wrong','/v1/consume'),('Bearer fixture-token','/grant')])
def test_consumption_service_rejects_unauthorized_or_other_operations(auth,path):
    class Authority:
        def consume(self,request):pytest.fail('No consumption operation authorized')
    Handler=handler(Authority(),'fixture-token')
    instance=Handler.__new__(Handler)
    class Connection:
        def settimeout(self,value):pass
    instance.connection=Connection()
    instance.path=path;instance.headers={'Authorization':auth,'Content-Length':'2'}
    instance.rfile=io.BytesIO(b'{}');instance.wfile=io.BytesIO()
    status=[]
    instance.send_response=lambda value:status.append(value)
    instance.send_header=lambda *a:None;instance.end_headers=lambda:None
    instance.do_POST()
    assert status==[403] and b'wrong' not in instance.wfile.getvalue()


def test_missing_consumer_evidence_keeps_paid_preflight_closed(reserved):
    state,cfg,github=reserved
    del cfg['trial']['call_consumer']
    from autose.broker import live_preflight
    with pytest.raises(GateError):live_preflight(cfg)


def test_expiry_after_consumption_burns_slot_without_provider_request(reserved,monkeypatch):
    state,cfg,github=reserved
    requests=[];transport(monkeypatch,requests)
    class ExpiresAfterConsume(FixtureConsumer):
        def consume(self,request):
            receipt=super().consume(request)
            monkeypatch.setattr(time,'time',lambda:cfg['trial']['expires_at']+1)
            return receipt
    broker=ResponsesBroker(cfg,ledger=Ledger(github),phase='implementation',consumer=ExpiresAfterConsume(Ledger(github),cfg))
    with pytest.raises(GateError,match='expired'):broker.ask(state,'implementation','JSON',{})
    assert requests==[] and state['usage']['calls']==0 and len(github.refs)==3
