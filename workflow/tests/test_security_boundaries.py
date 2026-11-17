"""Defensive regressions; no standalone attack harness or real service calls."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

import pytest

from autose import engine
from autose.common import GateError, digest, encoded, gate
from autose.executor import execute
from autose.verification import DOMAIN, verify_envelope, require_authoritative
from conftest import PYTHON, REPO, specification


def test_success_xml_and_zero_exit_cannot_authorize_testing_or_release(state,baseline_ids,tmp_path,monkeypatch):
    state['spec']=specification(state)
    state['source']['tests/test_autose_boundary.py']='def test_a():\n    assert False\ndef test_b():\n    assert False\n'
    state['test_map']={'AC-001':'tests/test_autose_boundary.py::test_a','AC-002':'tests/test_autose_boundary.py::test_b'}
    gate(state,'implementation','passed','controller test fixture')
    def diagnostic(argv,cwd,log,timeout,env):
        # A valid-looking report is an untrusted INPUT to the validator.
        root=ET.Element('testsuite',errors='0',failures='0',skipped='0')
        for klass,name in [*baseline_ids,['tests.test_autose_boundary','test_a'],['tests.test_autose_boundary','test_b']]:
            ET.SubElement(root,'testcase',classname=klass,name=name)
        ET.ElementTree(root).write(Path(cwd).parent/'output/junit.xml')
        return {'command':argv,'returncode':0,'timed_out':False,'seconds':0.01,'log':'fixture diagnostic'}
    monkeypatch.setattr('autose.executor._run',diagnostic)
    engine.test_stage(state,tmp_path/'run',baseline_ids=baseline_ids,local_fixture=True,python=PYTHON)
    assert state['execution']['diagnostic_passed'] is True
    assert state['execution']['authoritative'] is False and state['execution']['passed'] is False
    assert state['gates']['testing']['status']=='failed'
    assert 'disabled' in state['execution']['verification_error']
    with pytest.raises(GateError):engine.release(state,None)
    receipt=json.loads((tmp_path/'run/controller-receipt.json').read_text())
    assert receipt['returncode']==0 and receipt['identity']['source_sha256']==digest(encoded(state['source']))


def test_collection_early_exit_cannot_supply_completion(baseline,baseline_ids,tmp_path):
    source=copy.deepcopy(baseline)
    source['tests/test_autose_boundary.py']='import os\nos._exit(0)\ndef test_missing():\n    assert False\n'
    result=execute(source,tmp_path/'run',phase='testing',baseline_ids=baseline_ids,local_fixture=True,python=PYTHON)
    assert result['returncode']==0 and not result['timed_out']
    assert result['passed'] is False and result['authoritative'] is False
    assert 'missing/invalid JUnit' in result['validation_error']


@pytest.fixture
def keypair(tmp_path):
    private=tmp_path/'ephemeral-test-key.pem';public=tmp_path/'ephemeral-test-public.pem'
    subprocess.run(['openssl','genpkey','-algorithm','ED25519','-out',str(private)],check=True,capture_output=True)
    subprocess.run(['openssl','pkey','-in',str(private),'-pubout','-out',str(public)],check=True,capture_output=True)
    return private,public.read_text()


def signed_record(plan):
    def suite(ids,name):return {'completed':True,'genuine_result':'passed','exit_status':0,'failures':0,'errors':0,'skipped':0,
        'execution_id':plan['identity']['execution_id']+'-'+name,'case_ids':ids,'case_count':len(ids)}
    return {'schema':'autose-independent-tests-v1','identity':copy.deepcopy(plan['identity']),'plan_sha256':digest(encoded(plan)),
        'method':'independent-baseline-and-generated-execution','completed':True,'verdict':'passed','completed_at':time.time()-1,
        'expires_at':time.time()+300,'evidence_uri':'https://fixture.invalid/independent-run',
        'baseline':suite(plan['baseline_case_ids'],'baseline'),
        'generated':suite([['tests.test_autose_boundary','test_result']],'generated')}


def sign(record,keypair,tmp_path):
    private,public=keypair
    (tmp_path/'record').write_bytes(DOMAIN+encoded(record).encode())
    subprocess.run(['openssl','pkeyutl','-sign','-inkey',str(private),'-rawin','-in',str(tmp_path/'record'),
                    '-out',str(tmp_path/'signature')],check=True,capture_output=True)
    return {'record':record,'signature':base64.b64encode((tmp_path/'signature').read_bytes()).decode()}


@pytest.fixture
def verification_plan(baseline_ids):
    return {'identity':{'execution_id':'fixture-independent-request','source_sha256':'a'*64,'head_sha':'b'*40,
        'run_id':'1','run_attempt':'1','job_id':'tinydb-tests'},'baseline_case_ids':copy.deepcopy(baseline_ids),
        'generated_files':['tests/test_autose_boundary.py'],'test_map':{'AC-001':'tests/test_autose_boundary.py::test_result'}}


def test_independent_signature_and_all_228_cases_are_required(verification_plan,keypair,tmp_path):
    envelope=sign(signed_record(verification_plan),keypair,tmp_path)
    checked=verify_envelope(envelope,keypair[1],verification_plan)
    assert checked['verified'] is True and len(checked['case_ids'])==229
    envelope['record']['identity']['head_sha']='c'*40
    with pytest.raises(GateError,match='signature rejected'):verify_envelope(envelope,keypair[1],verification_plan)


def test_release_rechecks_independent_verdict_expiry(verification_plan):
    record=signed_record(verification_plan)
    result={'passed':True,'authoritative':True,'identity':verification_plan['identity'],'verification':{'record':record}}
    require_authoritative(result,'a'*64)
    record['expires_at']=0
    with pytest.raises(GateError,match='expired'):require_authoritative(result,'a'*64)


@pytest.mark.parametrize('defect',['source','head','run','attempt','job','nonce','plan','completion','exit','case_coverage','duplicates',
                                  'case_count','skips','failure','method','expired','suite_identity','missing_generated'])
def test_even_signed_incomplete_wrong_or_failed_evidence_is_rejected(verification_plan,keypair,tmp_path,defect):
    record=signed_record(verification_plan)
    fields={'source':'source_sha256','head':'head_sha','run':'run_id','attempt':'run_attempt','job':'job_id','nonce':'execution_id'}
    if defect in fields:record['identity'][fields[defect]]='different'
    if defect=='plan':record['plan_sha256']='f'*64
    if defect=='completion':record['completed']=False
    if defect=='exit':record['baseline']['exit_status']=1
    if defect=='case_coverage':record['baseline']['case_ids'].pop();record['baseline']['case_count']-=1
    if defect=='duplicates':record['baseline']['case_ids'].append(record['baseline']['case_ids'][0]);record['baseline']['case_count']+=1
    if defect=='case_count':record['baseline']['case_count']=0
    if defect=='skips':record['generated']['skipped']=1
    if defect=='failure':record['generated']['genuine_result']='failed'
    if defect=='method':record['method']='sign-candidate-junit-only'
    if defect=='expired':record['expires_at']=0
    if defect=='suite_identity':record['generated']['execution_id']=record['baseline']['execution_id']
    if defect=='missing_generated':record['generated']['case_ids']=[];record['generated']['case_count']=0
    envelope=sign(record,keypair,tmp_path)
    with pytest.raises(GateError):verify_envelope(envelope,keypair[1],verification_plan)


@pytest.mark.parametrize('field',['title','body'])
def test_all_issue_text_is_screened_before_admission(field,state,monkeypatch):
    from test_github import FakeAPI
    from autose.github import GitHub
    from autose.trial import approval_scope_hash, issue_scope_hash
    from trial_fixtures import config,prepare_state
    prepare_state(state);c=config(state)
    issue={**state['issue'],'state':'open','html_url':'fixture://issue/3','updated_at':'fixture'}
    synthetic='ghp_'+'x'*36
    issue[field]=synthetic
    c['trial']['issue_hash']=issue_scope_hash(issue);c['trial']['approval']['scope_sha256']=approval_scope_hash(c)
    api=FakeAPI(state['baseline'])
    def transport(method,path,body):
        if path.endswith('/issues/3'):return issue
        return api(method,path,body)
    from test_trial import trigger
    with pytest.raises(GateError,match='credential-like issue material') as error:
        engine.admit(trigger(),'issue_comment',GitHub(transport=transport),REPO,run_id='1',run_attempt=1,config=c)
    assert synthetic not in str(error.value)


def test_outbound_context_screen_precedes_consumption_and_provider(state,monkeypatch):
    from test_broker import broker_for
    monkeypatch.setenv('AUTOSE_MODEL_API_KEY','unit-test-only-placeholder')
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:pytest.fail('No service/provider transmission allowed'))
    broker=broker_for(state,'requirements')
    before=len(broker.ledger.github.refs)
    synthetic='ghp_'+'x'*36
    with pytest.raises(GateError,match='credential-like outbound input') as error:
        broker.ask(state,'requirements','JSON',{'nested':{'value':synthetic}})
    assert synthetic not in str(error.value) and state['usage']['calls']==0
    assert len(broker.ledger.github.refs)==before
