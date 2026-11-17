"""Independent authority supervisor. Candidate code never runs in this interpreter."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from .common import GateError, PIN, REPOSITORY, digest, encoded, require
from .executor import _run, junit
from .source import allowed, materialize, snapshot

POLICY='autose-isolated-rpc-v1'
MODULES=('authority_backend.py','authority_runtime.py','authority_bridge.py','authority_dsl.py','authority_worker.py','authority_fs.py',
         'verification.py','executor.py','source.py','common.py','github.py','engine.py','cli.py')
HERE=Path(__file__).resolve().parent


def trusted_code_hash():
    return digest(encoded({n:digest((HERE/n).read_bytes()) for n in MODULES}))


def read_trusted_suite(root,plan,name,environment):
    completion=root/'trusted-completion.json';report=root/'trusted-junit.xml'
    require(completion.is_file() and not completion.is_symlink() and completion.stat().st_size<1_000_000,'independent completion missing/invalid')
    done=json.loads(completion.read_text())
    require(done.get('identity')==plan['identity'] and done.get('suite')==name and
            done.get('environment_sha256')==digest(encoded(environment)),'independent completion identity/environment mismatch')
    require(done.get('completed') is True and type(done.get('exit_status')) is int and done['exit_status']==0 and
            type(done.get('worker_exit_status')) is int and done['worker_exit_status']==0 and done.get('worker_timed_out') is False and
            done.get('protocol_failed') is False and done.get('filesystem_failed') is False and
            done.get('collection_failed') is False,'independent completion/protocol invalid')
    cases=junit(report)
    require(done.get('report_sha256')==digest(report.read_bytes()),'independent report digest mismatch')
    collected=done.get('collected');phases=done.get('phases')
    require(isinstance(collected,list) and collected and len(collected)==len(set(collected)) and isinstance(phases,dict),
            'independent collection incomplete')
    require(set(phases)==set(collected) and all(v=={'setup':'passed','call':'passed','teardown':'passed'} for v in phases.values()),
            'independent case completion incomplete/failed')
    observed=[]
    for node in collected:
        require(isinstance(node,str) and node.count('::')==1,'independent collection identity invalid')
        path,function=node.split('::')
        observed.append((path[:-3].replace('/','.'),function))
    require(set(observed)==set(cases) and type(done.get('bridge_requests')) is int and done['bridge_requests']>0,
            'independent executed case coverage mismatch')
    if name=='baseline':require(set(cases)==set(map(tuple,plan['baseline_case_ids'])),'independent baseline coverage incomplete')
    return cases


def validate_plan(plan, repository, *, fixture=False):
    require(isinstance(plan,dict),'verification plan required')
    identity=plan.get('identity',{})
    expected=identity.get('expected_environment',{})
    require(isinstance(expected,dict) and set(expected)=={'policy','controller_sha256','image_digest'} and
            expected.get('policy')==POLICY and expected.get('controller_sha256')==trusted_code_hash(),'authority controller environment mismatch')
    require(identity.get('repository')==REPOSITORY,'authority repository mismatch')
    require(isinstance(identity.get('execution_id'),str) and re.fullmatch('[a-f0-9]{32}',identity['execution_id']),'authority nonce invalid')
    source=plan.get('source')
    require(isinstance(source,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in source.items()) and
            digest(encoded(source))==identity.get('source_sha256'),'authority source mismatch')
    baseline=snapshot(repository)
    for path,value in baseline.items():
        require(path in source,'authority baseline source missing')
        if path.startswith('tests/'):require(source[path]==value,'authority original test modified')
    require(len(source)<=27 and sum(len(v.encode()) for v in source.values())<=800_000,'authority source size')
    for path in source:
        if path not in baseline:allowed(path,'testing')
        elif path.startswith('tinydb/'):allowed(path,'implementation')
    ids=json.loads((Path(repository)/'workflow/config/baseline-case-ids.json').read_text())
    require(len(ids)==228 and len(set(map(tuple,ids)))==228 and plan.get('baseline_case_ids')==ids,'authority complete baseline inventory mismatch')
    generated=sorted(set(source)-set(baseline))
    require(plan.get('generated_files')==generated,'authority generated inventory mismatch')
    # Parse generated data before starting any worker. The parser never executes it.
    from . import authority_dsl
    for path in generated:
        try:authority_dsl.check(source[path])
        except (SyntaxError,RuntimeError):raise GateError('generated test program outside verifier policy') from None
    require(isinstance(plan.get('test_map'),dict),'authority acceptance mapping invalid')
    for node in plan['test_map'].values():
        require(isinstance(node,str) and node.count('::')==1 and node.split('::')[0] in generated,'authority acceptance mapping missing')
    binding=identity.get('binding')
    require(isinstance(binding,dict) and binding.get('kind') in ('issue','pull_request'),'authority execution binding missing')
    require(isinstance(identity.get('head_sha'),str) and re.fullmatch('[a-f0-9]{40}',identity['head_sha']),'authority exact commit required')
    if binding['kind']=='issue':
        require(plan['test_map'] and generated,'authority issue acceptance coverage required')
        require(type(binding.get('issue_number')) is int and binding['issue_number']>0 and
                isinstance(binding.get('issue_hash'),str) and re.fullmatch('[a-f0-9]{64}',binding['issue_hash']),'authority issue binding missing')
        require(binding.get('admitted_run_id')==identity.get('run_id'),'authority admitted run mismatch')
    else:
        require(type(binding.get('pull_request')) is int and binding['pull_request']>0,'authority PR binding missing')
    if not fixture:
        require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')==REPOSITORY,'authority hosted identity unavailable')
        require(identity.get('run_id')==os.environ.get('GITHUB_RUN_ID') and
                identity.get('run_attempt')==os.environ.get('GITHUB_RUN_ATTEMPT') and
                identity.get('job_id')==os.environ.get('AUTOSE_JOB_ID',os.environ.get('GITHUB_JOB')),'authority current run/job mismatch')
        from .github import GitHub
        api=GitHub();api.verify_repository()
        actual,commit=api.read_commit_source(identity['head_sha'])
        require(actual==source,'authority exact commit source mismatch')
        if binding['kind']=='issue':
            expected_message=f"autose: issue {binding['issue_number']} (run {binding['admitted_run_id']})\nIssue-SHA256: {binding['issue_hash']}\nSource-SHA256: {identity['source_sha256']}"
            require(commit.get('message','').rstrip('\n')==expected_message,'authority commit issue/run mismatch')
    return baseline,ids,generated


class IsolatedAuthority:
    def __init__(self,config,work_dir,repository=None):
        self.config=config
        self.work_dir=Path(work_dir).resolve()
        self.repository=Path(repository or HERE.parents[1]).resolve()

    def verify(self,plan):
        require(self.config.get('enabled') is True,'independent test authority disabled; testing gate blocked')
        return self._execute(plan,fixture=False)

    def run_fixture(self,plan):
        """ONLY pinned/coordinator-controlled inputs, never a sandbox or authority."""
        require(os.environ.get('GITHUB_ACTIONS')!='true','authority fixture forbidden on hosted runner')
        return self._execute(plan,fixture=True)

    def _execute(self,plan,fixture):
        baseline,ids,generated=validate_plan(plan,self.repository,fixture=fixture)
        image=None
        if not fixture:
            image=self.config.get('image_digest')
            require(isinstance(image,str) and re.fullmatch('sha256:[a-f0-9]{64}',image),'authority pinned image unavailable')
            actual=subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip()
            require(actual==image,'authority image mismatch')
            require(plan['identity']['expected_environment']['image_digest']==image,'authority requested image mismatch')
        # Trusted-only atomic reservation. Never delete failed/uncertain executions.
        self.work_dir.mkdir(parents=True,exist_ok=True)
        root=self.work_dir/plan['identity']['execution_id']
        try:root.mkdir()
        except FileExistsError:raise GateError('authority execution replay rejected') from None
        target=root/'candidate'
        materialize({p:v for p,v in plan['source'].items() if p.startswith('tinydb/')},target)
        tests=root/'trusted-tests';tests.mkdir()
        for path,value in baseline.items():
            if path.startswith('tests/'):
                p=tests/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
        for path in generated:(tests/path).write_text(plan['source'][path])
        import pytest,yaml
        environment={'policy':POLICY,'controller_sha256':trusted_code_hash(),'baseline_pin':PIN,
                     'baseline_tests_sha256':digest(encoded({p:v for p,v in baseline.items() if p.startswith('tests/')})),
                     'image_digest':image,'isolation':'local_fixture_unsandboxed' if fixture else 'docker_candidate_private_namespace',
                     'python':sys.version.split()[0],'python_binary_sha256':digest(Path(sys.executable).resolve().read_bytes()),
                     'pytest':pytest.__version__,'PyYAML':yaml.__version__,
                     'dependency_sha256':{module.__name__:digest(encoded({str(p.relative_to(Path(module.__file__).parent)):digest(p.read_bytes())
                         for p in Path(module.__file__).parent.rglob('*') if p.is_file() and p.suffix in ('.py','.so')})) for module in (pytest,yaml)}}
        require(environment['pytest']=='9.2.0' and environment['PyYAML']=='6.0.3','authority trusted dependency mismatch')
        suites={}
        for name,paths in (('baseline',[str(tests/p) for p in baseline if p.startswith('tests/test_')]),
                           ('generated',[str(tests/p) for p in generated])):
            suite=root/name;suite.mkdir();scratch=suite/'scratch';(scratch/'system').mkdir(parents=True)
            report=suite/'trusted-junit.xml';completion=suite/'trusted-completion.json'
            env={'PATH':os.defpath,'TMPDIR':str(scratch/'system'),'LANG':'C.UTF-8',
                 'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
            container='autose-authority-'+plan['identity']['execution_id']+'-'+name
            if fixture:
                worker=[sys.executable,'-I','-B',str(HERE/'authority_worker.py'),str(target)]
            else:
                worker=['docker','run','--rm','-i','--name',container,'--network=none','--read-only',
                    '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m','--cpus=1',
                    '--ulimit','fsize=16000000:16000000',
                    '--user',f'{os.getuid()}:{os.getgid()}','--tmpfs','/tmp:rw,noexec,nosuid,size=32m',
                    '--mount',f'type=bind,src={target},dst=/candidate,readonly',
                    '--mount',f'type=bind,src={HERE / "authority_worker.py"},dst=/trusted/worker.py,readonly',
                    '--mount',f'type=bind,src={scratch},dst={scratch}',
                    '-e','PYTHONDONTWRITEBYTECODE=1',image,'python','-I','-B','/trusted/worker.py','/candidate']
            control={'tests_root':str(tests),'scratch':str(scratch),'report':str(report),'completion':str(completion),
                     'identity':plan['identity'],'suite':name,'environment_sha256':digest(encoded(environment)),
                     'worker_argv':worker,'worker_cwd':str(suite),'worker_env':env,'worker_log':str(suite/'worker.log'),'test_paths':paths}
            (suite/'control.json').write_text(encoded(control))
            if not paths:
                suites[name]={'completed':True,'genuine_result':'passed','exit_status':0,'failures':0,'errors':0,
                              'skipped':0,'execution_id':plan['identity']['execution_id']+'-'+name,'case_ids':[],'case_count':0}
                continue
            try:
                process=_run([sys.executable,'-B',str(HERE/'authority_runtime.py'),'--control',str(suite/'control.json')],
                             tests,suite/'trusted-pytest.log',120,env)
            finally:
                if not fixture:
                    subprocess.run(['docker','rm','-f',container],capture_output=True,timeout=20)
            require(process['returncode']==0 and not process['timed_out'],'independent test execution failed; inspect trusted log')
            cases=read_trusted_suite(suite,plan,name,environment)
            suites[name]={'completed':True,'genuine_result':'passed','exit_status':0,'failures':0,'errors':0,'skipped':0,
                'execution_id':plan['identity']['execution_id']+'-'+name,'case_ids':[list(v) for v in cases],
                'case_count':len(cases),'report_sha256':digest(report.read_bytes()),'supervisor_exit_status':process['returncode'],
                'worker_exit_status':0,'worker_timed_out':False}
        record={'schema':'autose-isolated-authority-v2','identity':plan['identity'],'plan_sha256':digest(encoded(plan)),
                'method':'independent-baseline-and-generated-execution','completed':True,'verdict':'passed',
                'completed_at':time.time(),'expires_at':time.time()+1800,
                'evidence_uri':'https://fixture.invalid/local-authority' if fixture else f"https://github.com/{REPOSITORY}/actions/runs/{plan['identity']['run_id']}",
                'environment':environment,**suites}
        from .verification import validate_record
        cases=validate_record(record,plan)
        (root/'authority-record.json').write_text(encoded(record)+'\n')
        return {'verified':not fixture,'record':record,'case_ids':cases,
                'authority_policy':POLICY,'fixture_only':fixture}
