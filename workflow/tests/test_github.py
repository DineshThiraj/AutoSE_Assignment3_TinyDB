import copy
import hashlib
import time

import pytest

from autose import engine
from autose.common import GateError, REPOSITORY, digest, encoded, gate
from autose.github import APIError, GitHub
from autose.source import source_hash


def gitblob(s):
    raw=s.encode()
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


class FakeAPI:
    """In-memory REST contract double. No GitHub or provider traffic."""
    def __init__(self,baseline):
        self.baseline=baseline
        self.calls=[]
        self.permissions='admin'
        self.default='main'
        self.ci_mode='success'
        self.branch=None
        self.pr=None
        self.main='a'*40
        self.tree='c'*40
        self.reject_approval=False
        self.prs_override=None

    def __call__(self,method,path,body):
        self.calls.append((method,path,body))
        prefix='/repos/'+REPOSITORY
        assert path.startswith(prefix)
        endpoint=path[len(prefix):]
        if endpoint=='':return {'id':1461061397,'full_name':REPOSITORY,'owner':{'login':'DineshThiraj'},
            'fork':True,'parent':{'full_name':'msiemens/tinydb'},'default_branch':self.default,'has_issues':True,'archived':False}
        if endpoint.startswith('/collaborators/'):return {'permission':self.permissions}
        if endpoint=='/branches/main':return {'protected':True,'commit':{'sha':self.main}}
        if endpoint=='/branches/main/protection':return {'enforce_admins':{'enabled':True},
            'required_pull_request_reviews':{'bypass_pull_request_allowances':{'users':[],'teams':[],'apps':[]}},
            'allow_force_pushes':{'enabled':False},'allow_deletions':{'enabled':False},'required_status_checks':{'contexts':['tinydb-tests']}}
        if endpoint=='/issues/1':return {'number':1,'title':'issue','body':'Explicit scope.','state':'open','updated_at':'fixture','html_url':'fixture://issue/1'}
        if endpoint=='/git/ref/heads/main':return {'object':{'sha':self.main}}
        if endpoint.startswith('/git/trees/'):
            return {'sha':'d'*40,'truncated':False,'tree':[{'path':p,'mode':'100644','type':'blob','sha':gitblob(c)} for p,c in self.baseline.items()]}
        if endpoint.startswith('/pulls?'):
            if self.prs_override is not None:return self.prs_override
            return [] if self.pr is None else [copy.deepcopy(self.pr)]
        if endpoint=='/git/ref/heads/autose/issue-1':
            if not self.branch:raise APIError(404)
            return {'object':{'sha':self.branch}}
        if method=='POST' and endpoint=='/git/blobs':return {'sha':gitblob(body['content'])}
        if method=='POST' and endpoint=='/git/trees':return {'sha':self.tree}
        if method=='POST' and endpoint=='/git/commits':
            assert body['parents']==[self.branch or self.main]
            return {'sha':'b'*40}
        if endpoint=='/git/commits/'+'b'*40:return {'tree':{'sha':self.tree}}
        if method=='POST' and endpoint=='/git/refs':
            assert body['ref']=='refs/heads/autose/issue-1'
            self.branch=body['sha'];return {'object':{'sha':self.branch}}
        if method=='PATCH' and endpoint=='/git/refs/heads/autose/issue-1':
            assert body['force'] is False
            self.branch=body['sha'];return {'object':{'sha':self.branch}}
        if endpoint=='/pulls' and method=='POST':
            self.pr={'number':1,'state':'open','html_url':'fixture://pr/1','body':body['body'],
                'head':{'sha':self.branch,'repo':{'full_name':REPOSITORY}},
                'base':{'ref':'main','repo':{'full_name':REPOSITORY}}}
            return copy.deepcopy(self.pr)
        if endpoint=='/pulls/1' and method=='GET':return copy.deepcopy(self.pr)
        if endpoint.startswith('/actions/workflows/autose-ci.yml/runs?'):
            if self.ci_mode=='missing':return {'workflow_runs':[]}
            return {'workflow_runs':[{'id':1,'head_sha':'e'*40 if self.ci_mode=='stale' else self.branch,
                'event':'pull_request','path':'.github/workflows/autose-ci.yml','run_number':1,'run_attempt':1,
                'status':'in_progress' if self.ci_mode=='pending' else 'completed',
                'conclusion':'failure' if self.ci_mode=='failed' else 'success','html_url':'fixture://actions/1'}]}
        if endpoint.startswith('/actions/runs/1/jobs?'):
            return {'jobs':[{'name':'tinydb-tests','status':'completed','conclusion':'skipped' if self.ci_mode=='skipped' else 'success'}]}
        if endpoint=='/pulls/1/reviews':
            if self.reject_approval and body['event']=='APPROVE':raise APIError(422)
            return {'commit_id':body['commit_id'],'state':{'APPROVE':'APPROVED','REQUEST_CHANGES':'CHANGES_REQUESTED','COMMENT':'COMMENTED'}[body['event']],
                'html_url':'fixture://review/1'}
        raise AssertionError((method,path))


@pytest.fixture
def api(baseline):return FakeAPI(baseline)


@pytest.fixture
def hosted_contract_state(state):
    # Only paired with FakeAPI; no live token or actual hosted claim.
    state['execution_kind']='hosted'
    state['source']['tinydb/table.py']+='\n# fixture-only edit\n'
    state['tested_source_hash']=source_hash(state['source'])
    state['execution']={'passed':True,'authoritative':True,'identity':{'source_sha256':state['tested_source_hash']}}
    state['execution']['verification']={'record':{'identity':state['execution']['identity'],
        'completed':True,'verdict':'passed','expires_at':time.time()+300}}
    gate(state,'testing','passed','fixture full-suite gate')
    return state


@pytest.fixture
def event():return {'repository':{'full_name':REPOSITORY},'issue':{'number':1},
    'sender':{'login':'DineshThiraj','type':'User'},'action':'labeled','label':{'name':'autose'}}


def admission(event,api):
    from conftest import REPO
    return engine.admit(event,'issue_comment' if 'comment' in event else 'issues',GitHub(transport=api),REPO,
        run_id='1',run_attempt=1,config={},fixture=True)


def test_valid_issue_trigger_and_exact_comment(event,api):
    s=admission(event,api)
    assert s['execution_kind']=='local_fixture' and s['authorization']['permission']=='admin'
    event.update(action='created',comment={'body':'/autose'})
    assert admission(event,api)['issue']['number']==1


@pytest.mark.parametrize('body',[' /autose','/autose now','/autose\n','/AutoSE','echo /autose'])
def test_lookalike_comment_cannot_trigger(event,api,body):
    event.update(action='created',comment={'body':body})
    with pytest.raises(GateError):admission(event,api)


def test_untrusted_actor_bot_pr_and_lookup_outage_stop(event,api):
    api.permissions='read'
    with pytest.raises(GateError):admission(event,api)
    api.permissions='admin';event['sender']['type']='Bot'
    with pytest.raises(GateError):admission(event,api)
    event['sender']['type']='User';event['issue']['pull_request']={}
    with pytest.raises(GateError):admission(event,api)
    event['issue'].pop('pull_request')
    def denied(*args):raise APIError(403)
    from conftest import REPO
    with pytest.raises(APIError):engine.admit(event,'issues',GitHub(transport=denied),REPO,run_id='1',run_attempt=1,config={},fixture=True)


def test_duplicate_event_or_existing_issue_pr_stops_before_calls(event,api):
    api.prs_override=[{'number':1}]
    with pytest.raises(GateError,match='existing issue PR'):admission(event,api)


def test_controlled_publication_and_reconciliation_no_force(hosted_contract_state,api):
    gh=GitHub(transport=api)
    first=copy.deepcopy(gh.publish(hosted_contract_state))
    mutations_before=len([c for c in api.calls if c[0]=='POST' and c[1].endswith('/pulls')])
    second=gh.publish(hosted_contract_state)
    assert first['head_sha']==second['head_sha']=='b'*40
    assert mutations_before==len([c for c in api.calls if c[0]=='POST' and c[1].endswith('/pulls')])==1
    assert not any('/merge' in c[1] for c in api.calls)
    assert not any(c[0]!='GET' and c[1].endswith('/heads/main') for c in api.calls)
    assert all(c[2].get('force') is not True for c in api.calls if isinstance(c[2],dict))


def test_source_identity_and_changed_base_stop(hosted_contract_state,api):
    api.main='f'*40
    with pytest.raises(GateError,match='base changed'):GitHub(transport=api).publish(hosted_contract_state)
    api.main='a'*40;hosted_contract_state['source']['tinydb/table.py']+='changed'
    with pytest.raises(GateError,match='source identity'):GitHub(transport=api).publish(hosted_contract_state)


@pytest.mark.parametrize('mode',['stale','missing','pending'])
def test_stale_missing_and_pending_ci_never_pass(hosted_contract_state,api,mode):
    gh=GitHub(transport=api);gh.publish(hosted_contract_state);api.ci_mode=mode
    assert gh.ci(hosted_contract_state['publication'])['status']=='pending'


@pytest.mark.parametrize('mode',['failed','skipped'])
def test_failed_or_skipped_ci_cannot_pass(hosted_contract_state,api,mode):
    gh=GitHub(transport=api);gh.publish(hosted_contract_state);api.ci_mode=mode
    with pytest.raises(GateError):gh.ci(hosted_contract_state['publication'])


def test_posted_review_platform_rejection_is_not_false_approval(hosted_contract_state,api):
    gh=GitHub(transport=api);gh.publish(hosted_contract_state)
    gate(hosted_contract_state,'release','passed','fixture CI')
    hosted_contract_state['review']={'verdict':'APPROVE','summary':'Fixture-only verdict.','findings':[]}
    api.reject_approval=True
    engine.publish_review(hosted_contract_state,gh)
    assert hosted_contract_state['posted_review']['event']=='COMMENT'
    assert hosted_contract_state['gates']['review']['status']=='pending'


def test_self_review_change_request_comment_still_routes_honest_feedback(hosted_contract_state,api):
    def transport(method,path,body):
        if path.endswith('/reviews') and body['event']=='REQUEST_CHANGES':raise APIError(422)
        return api(method,path,body)
    gh=GitHub(transport=transport);gh.publish(hosted_contract_state)
    gate(hosted_contract_state,'release','passed','fixture CI')
    hosted_contract_state['review']={'verdict':'REQUEST_CHANGES','summary':'Fixture-only request.',
        'findings':[{'path':'tinydb/table.py','line':1,'stage':'implementation','evidence':'fixture feedback'}]}
    engine.publish_review(hosted_contract_state,gh)
    assert hosted_contract_state['posted_review']['event']=='COMMENT'
    assert hosted_contract_state['next_route']=='implementation'
    assert hosted_contract_state['gates']['review']['status']=='failed'


def test_fixtures_cannot_publish_through_real_client(state,api):
    gate(state,'testing','passed','fixture')
    with pytest.raises(GateError,match='fixture'):GitHub(transport=api).publish(state)


def test_rules_reader_needs_real_setup_record_and_unchanged_rules():
    rules=[{'type':t} for t in ('pull_request','non_fast_forward','deletion')]+[
        {'type':'required_status_checks','parameters':{'required_status_checks':[{'context':'tinydb-tests'}]}}]
    gh=GitHub(transport=lambda *args:rules)
    record={'repository':REPOSITORY,'verified':True,'no_bypass_verified':True,'evidence':'fixture only',
        'verified_at':time.time()-1,'expires_at':time.time()+100,'effective_rules_sha256':digest(encoded(rules))}
    assert gh.verify_rules_preflight(record)['method']=='effective_rules_plus_verified_admin_preflight'
    for key,value in [('verified',False),('no_bypass_verified',False),('expires_at',0),('effective_rules_sha256','wrong')]:
        changed={**record,key:value}
        with pytest.raises(GateError):gh.verify_rules_preflight(changed)
