"""Actual supervisor/bridge checks; unsandboxed runs use only controlled fixtures."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pytest

from autose.common import GateError,REPOSITORY,digest,encoded
from autose.authority_backend import IsolatedAuthority,POLICY,trusted_code_hash,validate_plan,read_trusted_suite
from autose.authority_bridge import Session,BridgeError
from autose.authority_dsl import check,Evaluator
from autose.verification import validate_record,require_authoritative
from conftest import REPO,TESTS


def plan_for(source,baseline_ids):
    return {'identity':{'repository':REPOSITORY,'execution_id':uuid.uuid4().hex,'head_sha':'b'*40,
        'source_sha256':digest(encoded(source)),'run_id':'1','run_attempt':'1','job_id':'tests',
        'binding':{'kind':'issue','issue_number':3,'issue_hash':'c'*64,'admitted_run_id':'1','base_sha':'a'*40},
        'expected_environment':{'policy':POLICY,'controller_sha256':trusted_code_hash(),'image_digest':None}},
        'source':source,'baseline_case_ids':copy.deepcopy(baseline_ids),
        'generated_files':sorted(p for p in source if p.startswith('tests/test_autose_')),
        'test_map':{'AC-001':'tests/test_autose_remove.py::test_repeated_ids','AC-002':'tests/test_autose_remove.py::test_preserve_tables_and_cache'}}


@pytest.fixture
def controlled_source(baseline):
    source=copy.deepcopy(baseline)
    source['tinydb/table.py']=source['tinydb/table.py'].replace('requested_ids = list(doc_ids)','requested_ids = list(dict.fromkeys(doc_ids))')
    source['tests/test_autose_remove.py']=TESTS
    return source


def test_actual_trusted_baseline_and_interpreted_generated_suite(controlled_source,baseline_ids,tmp_path):
    plan=plan_for(controlled_source,baseline_ids)
    backend=IsolatedAuthority({'enabled':False},tmp_path,REPO)
    checked=backend.run_fixture(plan)
    assert checked['verified'] is False and checked['fixture_only'] is True
    assert checked['record']['baseline']['case_count']==228
    assert checked['record']['generated']['case_count']==4
    assert len(checked['case_ids'])==232
    assert checked['record']['environment']['isolation']=='local_fixture_unsandboxed'
    with pytest.raises(GateError):
        require_authoritative({'passed':True,'authoritative':True,'identity':plan['identity'],'verification':checked})
    with pytest.raises(GateError,match='replay'):backend.run_fixture(plan)
    with pytest.raises(GateError,match='disabled'):backend.verify(plan)


def test_actual_unfixed_defect_cannot_pass_generated_verification(baseline,baseline_ids,tmp_path):
    source=copy.deepcopy(baseline);source['tests/test_autose_remove.py']=TESTS
    plan=plan_for(source,baseline_ids)
    with pytest.raises(GateError,match='execution failed'):
        IsolatedAuthority({'enabled':False},tmp_path,REPO).run_fixture(plan)
    run=tmp_path/plan['identity']['execution_id']
    assert (run/'baseline/trusted-completion.json').is_file()
    assert not (run/'authority-record.json').exists()
    xml=ET.parse(run/'generated/trusted-junit.xml')
    assert list(xml.iter('failure'))
    assert 'KeyError' in (run/'generated/trusted-pytest.log').read_text()


def test_false_generated_assertion_runs_in_trusted_evaluator(controlled_source,baseline_ids,tmp_path):
    controlled_source['tests/test_autose_remove.py']='def test_repeated_ids(db):\n    assert False\ndef test_preserve_tables_and_cache(db):\n    assert False\n'
    plan=plan_for(controlled_source,baseline_ids)
    with pytest.raises(GateError,match='execution failed'):
        IsolatedAuthority({'enabled':False},tmp_path,REPO).run_fixture(plan)
    xml=ET.parse(tmp_path/plan['identity']['execution_id']/'generated/trusted-junit.xml')
    assert len(list(xml.iter('failure')))==4


@pytest.mark.parametrize('program',[
    'import os\nos._exit(0)\ndef test_x(db):\n    assert False\n',
    'def test_x(db):\n    open("junit.xml","w").write("success")\n    assert True\n',
    'def test_x(db):\n    exec("assert True")\n    assert False\n',
    'def test_x(db):\n    assert db.__class__\n',
    '@unknown\ndef test_x(db):\n    assert True\n',
    'def test_x(db):\n    while True:\n        pass\n    assert True\n',
])
def test_generated_code_cannot_execute_or_write_verdict(program,controlled_source,baseline_ids,tmp_path):
    controlled_source['tests/test_autose_remove.py']=program
    plan=plan_for(controlled_source,baseline_ids)
    with pytest.raises(GateError,match='outside verifier policy'):
        IsolatedAuthority({'enabled':False},tmp_path,REPO).run_fixture(plan)
    assert not list(tmp_path.iterdir())


def test_interpreter_early_return_and_unbounded_data_are_not_success():
    _,functions=check('def test_x(db):\n    return\n    assert False\n')
    with pytest.raises(BridgeError,match='not executed'):Evaluator({'db':None}).run(functions[0])
    with pytest.raises(BridgeError):check('def test_x(db):\n    assert vars(db)\n')


@pytest.mark.parametrize('defect',['baseline_bytes','baseline_ids','source_hash','issue','run','commit','environment','files','mapping'])
def test_mismatched_plan_is_rejected_before_execution(controlled_source,baseline_ids,tmp_path,defect):
    plan=plan_for(controlled_source,baseline_ids)
    if defect=='baseline_bytes':
        plan['source']['tests/test_queries.py']+='\n# changed\n'
        plan['identity']['source_sha256']=digest(encoded(plan['source']))
    if defect=='baseline_ids':plan['baseline_case_ids'].pop()
    if defect=='source_hash':plan['identity']['source_sha256']='0'*64
    if defect=='issue':plan['identity']['binding']['issue_hash']='missing'
    if defect=='run':plan['identity']['binding']['admitted_run_id']='2'
    if defect=='commit':plan['identity']['head_sha']=None
    if defect=='environment':plan['identity']['expected_environment']['controller_sha256']='0'*64
    if defect=='files':plan['generated_files']=[]
    if defect=='mapping':plan['test_map']={}
    with pytest.raises(GateError):validate_plan(plan,REPO,fixture=True)
    assert not list(tmp_path.iterdir())


def trusted_pair(root,plan):
    environment={'policy':POLICY,'controller_sha256':trusted_code_hash(),'image_digest':None}
    ids=plan['baseline_case_ids']
    xml=ET.Element('testsuite',errors='0',failures='0',skipped='0')
    for klass,name in ids:ET.SubElement(xml,'testcase',classname=klass,name=name)
    ET.ElementTree(xml).write(root/'trusted-junit.xml')
    nodes=[k.replace('.','/')+'.py::'+v for k,v in ids]
    done={'identity':plan['identity'],'suite':'baseline','environment_sha256':digest(encoded(environment)),
          'completed':True,'exit_status':0,'protocol_failed':False,'filesystem_failed':False,'collection_failed':False,
          'worker_exit_status':0,'worker_timed_out':False,
          'collected':nodes,'phases':{n:{p:'passed' for p in ('setup','call','teardown')} for n in nodes},
          'bridge_requests':100,'report_sha256':digest((root/'trusted-junit.xml').read_bytes())}
    (root/'trusted-completion.json').write_text(encoded(done))
    return environment,done


@pytest.mark.parametrize('defect',['missing','stale_nonce','run','commit','issue','environment','report','exit','coverage','phase','protocol','filesystem','empty_bridge','worker_exit','worker_timeout'])
def test_forged_stale_replayed_or_incomplete_completion_is_denied(controlled_source,baseline_ids,tmp_path,defect):
    plan=plan_for(controlled_source,baseline_ids)
    env,done=trusted_pair(tmp_path,plan)
    assert len(read_trusted_suite(tmp_path,plan,'baseline',env))==228
    if defect=='missing':(tmp_path/'trusted-completion.json').unlink()
    elif defect=='report':(tmp_path/'trusted-junit.xml').write_text('<testsuite/>')
    else:
        done=copy.deepcopy(done)
        if defect=='stale_nonce':done['identity']['execution_id']='f'*32
        if defect=='run':done['identity']['run_id']='2'
        if defect=='commit':done['identity']['head_sha']='f'*40
        if defect=='issue':done['identity']['binding']['issue_hash']='f'*64
        if defect=='environment':done['environment_sha256']='f'*64
        if defect=='exit':done['exit_status']=1
        if defect=='coverage':done['collected'].pop()
        if defect=='phase':next(iter(done['phases'].values())).pop('call')
        if defect=='protocol':done['protocol_failed']=True
        if defect=='filesystem':done['filesystem_failed']=True
        if defect=='empty_bridge':done['bridge_requests']=0
        if defect=='worker_exit':done['worker_exit_status']=1
        if defect=='worker_timeout':done['worker_timed_out']=True
        (tmp_path/'trusted-completion.json').write_text(encoded(done))
    with pytest.raises(GateError):read_trusted_suite(tmp_path,plan,'baseline',env)


@pytest.mark.parametrize('message',[
    {'kind':'verdict','passed':True},
    {'kind':'result','id':999,'value':{'kind':'value','value':True}},
    {'kind':'callback','id':1,'target':123,'method':'write','args':[],'kwargs':{}},
    {'kind':'result','id':1,'error':{'type':'SystemExit','message':'0'}},
    {'kind':'result','id':1,'value':{'kind':'pickle','value':'never decoded'}},
    {'kind':'result','id':1},
])
def test_candidate_frames_cannot_authorize_or_execute_host_code(message,tmp_path):
    # Harmless fixture peer emits one data frame; no candidate Python is imported.
    code='import sys,json; sys.stdin.buffer.readline(); print('+repr(json.dumps(message))+',flush=True); sys.stdin.buffer.readline()'
    process=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,bufsize=0)
    session=Session(process,tmp_path,timeout=2)
    try:
        with pytest.raises(BridgeError):session.request('symbol',module='tinydb',name='TinyDB')
        assert session.poisoned is True
    finally:session.close()


def test_shared_fixture_symlinks_and_callback_descriptors_cannot_write_verdict(tmp_path):
    scratch=tmp_path/'scratch';scratch.mkdir()
    protected=tmp_path/'trusted-verdict';protected.write_text('unchanged')
    (scratch/'alias').symlink_to(protected)
    script=REPO/'workflow/autose/authority_fs.py'
    code='''import sys,importlib.util
spec=importlib.util.spec_from_file_location("guard",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.install(sys.argv[2]);m.enter()
for path in (sys.argv[3],sys.argv[2]+"/alias",1):
    try:open(path,"w")
    except OSError:pass
    else:raise AssertionError("forbidden write accepted")
m.leave()
assert m.VIOLATIONS==3
'''
    p=subprocess.run([sys.executable,'-B','-c',code,str(script),str(scratch),str(protected)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert protected.read_text()=='unchanged'


def test_enabled_backend_without_pinned_image_still_fails_closed(controlled_source,baseline_ids,tmp_path,monkeypatch):
    plan=plan_for(controlled_source,baseline_ids)
    # Fixture validation is exercised separately; do not invent a hosted identity.
    monkeypatch.setattr('autose.authority_backend.validate_plan',lambda *a,**k:validate_plan(plan,REPO,fixture=True))
    with pytest.raises(GateError,match='pinned image'):
        IsolatedAuthority({'enabled':True,'image_digest':None},tmp_path,REPO).verify(plan)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('defect',['hosted','repository','run','attempt','job','source','message'])
def test_production_identity_and_exact_remote_commit_are_required(controlled_source,baseline_ids,monkeypatch,defect):
    plan=plan_for(controlled_source,baseline_ids)
    for key,value in {'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':REPOSITORY,'GITHUB_RUN_ID':'1',
                      'GITHUB_RUN_ATTEMPT':'1','AUTOSE_JOB_ID':'tests'}.items():monkeypatch.setenv(key,value)
    identity=plan['identity'];binding=identity['binding']
    message=f"autose: issue 3 (run 1)\nIssue-SHA256: {binding['issue_hash']}\nSource-SHA256: {identity['source_sha256']}"
    actual=copy.deepcopy(controlled_source)
    if defect=='hosted':monkeypatch.delenv('GITHUB_ACTIONS')
    if defect=='repository':monkeypatch.setenv('GITHUB_REPOSITORY','unapproved/repository')
    if defect=='run':monkeypatch.setenv('GITHUB_RUN_ID','2')
    if defect=='attempt':monkeypatch.setenv('GITHUB_RUN_ATTEMPT','2')
    if defect=='job':monkeypatch.setenv('AUTOSE_JOB_ID','different')
    if defect=='source':actual['tinydb/table.py']+='\n# different immutable commit\n'
    if defect=='message':message='another issue/run'
    class ReadOnlyAPI:
        def verify_repository(self):pass
        def read_commit_source(self,head):
            assert head==identity['head_sha']
            return actual,{'message':message}
    monkeypatch.setattr('autose.github.GitHub',ReadOnlyAPI)
    with pytest.raises(GateError):validate_plan(plan,REPO)


def test_missing_trusted_execution_cannot_adopt_a_successful_candidate_report(controlled_source,baseline_ids,tmp_path,monkeypatch):
    plan=plan_for(controlled_source,baseline_ids)
    def no_execution(argv,cwd,log,timeout,env):
        # Even a successful process return is insufficient without trusted completion.
        Path(log).write_text('controlled missing-execution fixture')
        return {'returncode':0,'timed_out':False}
    monkeypatch.setattr('autose.authority_backend._run',no_execution)
    with pytest.raises(GateError,match='completion missing'):
        IsolatedAuthority({'enabled':False},tmp_path,REPO).run_fixture(plan)
    assert not (tmp_path/plan['identity']['execution_id']/'authority-record.json').exists()


def test_actual_baseline_retains_custom_mapping_type_checks(controlled_source,baseline_ids,tmp_path):
    controlled_source['tinydb/table.py']=controlled_source['tinydb/table.py'].replace(
        'isinstance(document, Mapping)','isinstance(document, dict)')
    plan=plan_for(controlled_source,baseline_ids)
    with pytest.raises(GateError,match='execution failed'):
        IsolatedAuthority({'enabled':False},tmp_path,REPO).run_fixture(plan)
    run=tmp_path/plan['identity']['execution_id']
    assert not (run/'authority-record.json').exists()
    assert 'test_insert' in (run/'baseline/trusted-pytest.log').read_text()
    assert list(ET.parse(run/'baseline/trusted-junit.xml').iter('failure'))


@pytest.mark.parametrize('mode',['wrong_image','missing_completion'])
def test_production_mount_boundary_and_image_fail_closed(controlled_source,baseline_ids,tmp_path,monkeypatch,mode):
    plan=plan_for(controlled_source,baseline_ids)
    image='sha256:'+'f'*64
    plan['identity']['expected_environment']['image_digest']=image
    monkeypatch.setattr('autose.authority_backend.validate_plan',lambda *a,**k:validate_plan(plan,REPO,fixture=True))
    original=subprocess.check_output
    def inspect(argv,**kwargs):
        if argv[0]=='docker':return ('sha256:'+'e'*64) if mode=='wrong_image' else image
        return original(argv,**kwargs)
    monkeypatch.setattr('autose.authority_backend.subprocess.check_output',inspect)
    # Only cleanup is intercepted here; the supervisor process is intercepted below.
    original_run=subprocess.run
    def cleanup_only(argv,**kwargs):
        if argv[0]=='docker':return None
        return original_run(argv,**kwargs)
    monkeypatch.setattr('autose.authority_backend.subprocess.run',cleanup_only)
    controls=[]
    def not_executed(argv,cwd,log,timeout,env):
        control=json.loads(Path(argv[-1]).read_text());controls.append(control)
        worker=control['worker_argv']
        assert worker[:2]==['docker','run']
        assert '--network=none' in worker and '--read-only' in worker
        assert '--cap-drop=ALL' in worker and '--security-opt=no-new-privileges' in worker
        mounts=[worker[i+1] for i,v in enumerate(worker) if v=='--mount']
        assert len(mounts)==3
        assert any('dst=/candidate,readonly' in m for m in mounts)
        assert any('dst=/trusted/worker.py,readonly' in m for m in mounts)
        assert all('trusted-junit' not in m and 'control.json' not in m and 'completion' not in m for m in mounts)
        assert set(env)=={'PATH','TMPDIR','LANG','PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD'}
        assert control['worker_env']==env
        return {'returncode':0,'timed_out':False}
    monkeypatch.setattr('autose.authority_backend._run',not_executed)
    with pytest.raises(GateError,match='image mismatch' if mode=='wrong_image' else 'completion missing'):
        IsolatedAuthority({'enabled':True,'image_digest':image},tmp_path,REPO).verify(plan)
    assert len(controls)==(mode=='missing_completion')
    assert not list(tmp_path.rglob('authority-record.json'))
