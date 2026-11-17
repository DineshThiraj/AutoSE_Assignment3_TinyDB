"""Narrow one-use consumption authority; broker has no GitHub write token.

The server owns ledger writes. It can consume existing fixed slots, never mint a
grant or call a provider. Its credential authorizes only this operation.
"""
import os
import re

from .common import digest, encoded, require, sha
from .services import post_json
from .trial import INPUT_CEILING, PHASE_CALLS, RATES, integer, money, preflight


def call_request(state, grant, phase, index, request_hash):
    job_id=os.environ.get('AUTOSE_JOB_ID') if os.environ.get('GITHUB_ACTIONS')=='true' else grant['job_id']
    require(job_id==grant['job_id'],'paid job identity mismatch')
    return {'grant_sha':state['trial_grant']['sha'],'sequence':state['trial_grant']['sequence'],
            'identity':grant['identity'],'phase':phase,'job_id':job_id,'call_index':index,'request_sha256':request_hash}


def slot_name(request):
    return f"consume-{request['sequence']}-{request['call_index']}"


def validate_request(ledger, config, request):
    t=preflight(config)
    require(isinstance(request,dict),'invalid consumption request')
    require(set(request)=={'grant_sha','sequence','identity','phase','job_id','call_index','request_sha256'},'unexpected consumption fields')
    seq=integer(request.get('sequence'),1,24,'grant sequence')
    commit,grant=ledger.read('grant-'+str(seq))
    require(commit==sha(request.get('grant_sha')) and grant['kind']=='grant','consumption grant mismatch')
    require(request.get('identity')==grant['identity'] and grant['identity']['config_hash']==digest(encoded(config)), 'consumption identity mismatch')
    owner=grant['identity']
    require(owner['trial_id']==t['id'] and owner['issue_hash']==t['issue_hash'] and owner['run_attempt']==1,'consumption trial mismatch')
    _,claim=ledger.read('claim')
    require(claim=={'kind':'claim','identity':owner},'consumption claim mismatch')
    require(request.get('phase')==grant['phase'] and request.get('job_id')==grant['job_id'],'consumption job mismatch')
    integer(request.get('call_index'),1,grant['calls'],'call slot')
    require(grant['calls']==PHASE_CALLS[grant['phase']] and grant['input_ceiling']==INPUT_CEILING
            and grant['max_output_tokens']==config['max_output_tokens'],'consumption envelope mismatch')
    totals=grant['totals']
    integer(totals['calls'],grant['calls'],t['max_calls'],'reserved calls')
    integer(totals['tokens'],grant['calls']*(INPUT_CEILING+config['max_output_tokens']),t['max_tokens'],'reserved tokens')
    integer(totals['nano_usd'],1,money(t['max_usd']),'reserved USD')
    require(totals['tokens']==totals['calls']*(INPUT_CEILING+config['max_output_tokens']),'reserved token accounting mismatch')
    per_call=INPUT_CEILING*max(v for k,v in RATES.items() if k!='output')+config['max_output_tokens']*RATES['output']
    require(totals['nano_usd']==totals['calls']*per_call,'reserved cost accounting mismatch')
    require(isinstance(request.get('request_sha256'),str) and re.fullmatch('[a-f0-9]{64}',request['request_sha256']),'invalid request hash')
    return commit,grant


class ConsumptionAuthority:
    """Deploy on a separate trusted host, never in a broker/reviewer job."""
    def __init__(self,ledger,config):self.ledger,self.config=ledger,config

    def consume(self,request):
        parent,_=validate_request(self.ledger,self.config,request)
        # Recheck expiry after remote reads, before the atomic irreversible write.
        preflight(self.config)
        record={'kind':'consumed','request':request}
        receipt=self.ledger.create(slot_name(request),record,parent)
        return {'receipt_sha':receipt}


class CallConsumer:
    def __init__(self,config,ledger):self.config,self.ledger=config,ledger

    def consume(self,request):
        preflight(self.config)
        result=post_json(self.config['trial']['call_consumer']['url'],request,
                         os.environ.get('AUTOSE_CONSUMER_TOKEN'),maximum=100_000)
        # The response alone cannot authorize inference: read the durable record.
        commit,record=self.ledger.read(slot_name(request))
        require(commit==sha(result.get('receipt_sha')) and record=={'kind':'consumed','request':request},'consumption receipt mismatch')
        preflight(self.config)
        return {'receipt_sha':commit,'slot':slot_name(request),'request_sha256':request['request_sha256']}
