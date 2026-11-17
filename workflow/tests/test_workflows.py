import json
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from conftest import REPO


def workflow(name):
    return yaml.safe_load((REPO/'.github/workflows'/name).read_text())


def test_static_job_graph_no_cycles_and_only_two_review_rounds():
    main=workflow('autose.yml')
    jobs=main['jobs']
    done=set()
    def visit(name,active):
        assert name not in active,'cycle in Actions jobs'
        if name in done:return
        for need in jobs[name].get('needs',[]):
            assert need in jobs,'unknown dependency'
            visit(need,active|{name})
        done.add(name)
    for name in jobs:visit(name,set())
    assert len(done)==62
    assert sum(j.get('with',{}).get('phase')=='freeze-candidate' for j in jobs.values())==4
    assert jobs['trial_claim']['with']['phase']=='claim'
    assert jobs['trial_claim']['needs']==['admission']
    assert sum(j.get('with',{}).get('phase')=='review' for j in jobs.values())==2
    assert sum(j.get('with',{}).get('phase')=='implementation' for j in jobs.values())==4
    assert main['concurrency']['cancel-in-progress'] is False
    assert 'pull_request_target' not in main['on']
    assert set(main['on'])=={'issues','issue_comment'}
    for name,job in jobs.items():
        if name.endswith('_release'):
            assert "outputs.passed == 'true'" in job['if']
        if 'AUTOSE_MODEL_API_KEY' in job.get('secrets',{}):
            assert job['uses'].endswith('autose-broker.yml')
            reservation=jobs[job['needs'][0]]
            assert reservation['uses'].endswith('autose-ledger.yml')
            assert reservation['with']['phase']=='reserve'
            assert reservation['with']['target_phase']==job['with']['phase']
            assert "outputs.ready == 'true'" in job['if']
        if name.startswith('r2'):
            assert 'r2_start' in jobs or name=='r2_start'


def test_workflow_mirrors_and_credential_boundaries():
    for path in (REPO/'.github/workflows').glob('*.yml'):
        assert path.read_bytes()==(REPO/'workflow/workflows'/path.name).read_bytes()
    for kind in ('execute','data','broker'):
        doc=workflow(f'autose-{kind}.yml')
        job=doc['jobs']['phase']
        assert all(v=='read' for v in job['permissions'].values())
        assert job['steps'][0]['with']['persist-credentials'] is False
        source=(REPO/'.github/workflows'/f'autose-{kind}.yml').read_text()
        if kind!='broker':assert 'MODEL_API_KEY' not in source
    broker=workflow('autose-broker.yml')
    assert set(broker['on']['workflow_call']['secrets'])=={'AUTOSE_MODEL_API_KEY','AUTOSE_CONSUMER_TOKEN'}
    ledger=workflow('autose-ledger.yml')
    assert ledger['jobs']['phase']['permissions']=={'contents':'write','actions':'read'}
    assert 'secrets' not in ledger['on']['workflow_call']
    assert 'MODEL_API_KEY' not in json.dumps(ledger)
    assert 'docker' not in json.dumps(ledger)
    ci=workflow('autose-ci.yml')
    steps=ci['jobs']['tinydb-tests']['steps']
    assert steps[0]['with']['ref']=='${{ github.event.pull_request.base.sha }}'
    assert steps[1]['with']['ref']=='${{ github.event.pull_request.head.sha }}'
    assert steps[0]['with']['path']=='trusted' and steps[1]['with']['path']=='candidate'


def test_inherited_automation_cannot_bypass_isolated_ci():
    for name in ('ci-workflow.yml','publish-workflow.yml'):
        doc=workflow(name)
        assert set(doc['on'])=={'workflow_dispatch'}
        assert doc['permissions']=={}
        assert set(doc['jobs'])=={'notice'}
        assert all('uses' not in s for s in doc['jobs']['notice']['steps'])
        assert 'secrets.' not in json.dumps(doc)
        assert (REPO/'workflow/upstream-reference'/name).is_file()


def test_generation_is_portable():
    source=(REPO/'workflow/generate_workflows.py').read_text()
    assert '/home/user/' not in source and 'Path(__file__)' in source


def test_artifact_recovery_selects_current_run_latest_attempt(tmp_path):
    if not shutil.which('node'):pytest.skip('Node unavailable for trusted artifact-discovery unit test')
    script=REPO/'workflow/artifact_input.js'
    runner=tmp_path/'test.cjs'
    runner.write_text('''const select = require(process.argv[2]);
const assert = require('assert');
let output;
const args = {context:{repo:{owner:'DineshThiraj',repo:'AutoSE_Assignment3_TinyDB'},runId:123},
core:{setOutput:(k,v)=>{if(k==='ids')output=v;}}, pattern:'r1a1_result', multiple:false,
github:{rest:{actions:{listWorkflowRunArtifacts:async p=>{
 assert.equal(p.run_id,123);
 return {data:{artifacts:[
 {id:1,name:'r1a1_result-attempt-1',expired:false},
 {id:2,name:'r1a1_result-attempt-2',expired:false},
 {id:3,name:'r1a1_result-attempt-3',expired:false},
 {id:4,name:'unrelated-attempt-2',expired:false}]}};
}}}}};
process.env.GITHUB_RUN_ATTEMPT='2';
select(args).then(()=>{assert.equal(output,'2');console.log('current-run recovery contract passed');}).catch(e=>{console.error(e);process.exit(1)});
''')
    result=subprocess.run(['node',str(runner),str(script)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
