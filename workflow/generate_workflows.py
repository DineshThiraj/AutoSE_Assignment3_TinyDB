from pathlib import Path
import shutil,yaml
repo=Path(__file__).resolve().parent.parent
baseout={k:{'value':'${{ jobs.phase.outputs.'+k+' }}'} for k in ('ready','passed','retry','repair','want_tests','base_sha')}
inputs={k:{'required':True,'type':'string'} for k in ('phase','prefix','prior','base_sha')}
for kind in ('broker','execute','publish','data'):
 permissions={'contents':'read','actions':'read'}
 if kind=='publish': permissions.update({'contents':'write','pull-requests':'write','actions':'read'})
 steps=[{'uses':'actions/checkout@v4','with':{'ref':'${{ inputs.base_sha }}','fetch-depth':0,'persist-credentials':False}},
        {'uses':'actions/setup-python@v5','with':{'python-version':'3.12'}}]
 steps.append({'uses':'actions/github-script@v7','id':'artifacts',
  'env':{'PRIOR':'${{ inputs.prior }}','MULTIPLE':'true' if kind=='data' else 'false','PHASE':'${{ inputs.phase }}'},
  'with':{'script':"await require('./workflow/artifact_input.js')({github, context, core, pattern: process.env.PRIOR, multiple: process.env.MULTIPLE === 'true' && process.env.PHASE !== 'repair'});"}})
 steps.append({'uses':'actions/download-artifact@v4','with':{'artifact-ids':'${{ steps.artifacts.outputs.ids }}',
  'path':'input','merge-multiple':kind!='data'}})
 if kind=='execute':
  steps.append({'name':'Build trusted test environment before target mount','run':'docker build -t autose-pytest:trusted -f workflow/Dockerfile workflow\ndocker image inspect autose-pytest:trusted --format "{{.Id}}" > image-id.txt'})
 env={'PYTHONPATH':'workflow','PHASE':'${{ inputs.phase }}'}
 if kind=='broker': env['AUTOSE_MODEL_API_KEY']='${{ secrets.AUTOSE_MODEL_API_KEY }}'
 if kind=='publish': env['GITHUB_TOKEN']='${{ github.token }}'
 # Data repair takes a named input artifact, unlike selection of multiple artifacts.
 command='python -m autose.cli "$PHASE" --input input --output out'
 steps.extend([{'name':'Execute trusted phase','id':'run','env':env,'run':command},
               {'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'${{ inputs.prefix }}-attempt-${{ github.run_attempt }}','path':'out/','if-no-files-found':'error','retention-days':90}}])
 phase={'runs-on':'ubuntu-latest','timeout-minutes':20 if kind=='broker' else 10,'permissions':permissions,
        'outputs':{k:'${{ steps.run.outputs.'+k+' }}' for k in baseout},'steps':steps}
 call={'inputs':inputs,'outputs':baseout}
 if kind=='broker': call['secrets']={'AUTOSE_MODEL_API_KEY':{'required':False}}
 doc={'name':'AutoSE '+kind+' phase','on':{'workflow_call':call},'permissions':{},'jobs':{'phase':phase}}
 (repo/'.github/workflows'/f'autose-{kind}.yml').write_text(yaml.safe_dump(doc,sort_keys=False,width=120))

jobs={}
def guard(prev,key='ready'):
 return f"always() && needs.{prev}.result == 'success' && needs.{prev}.outputs.{key} == 'true'"
def call(name,phase,previous,kind='broker',condition=None,needs=None,pattern=None):
 perms={'contents':'read','actions':'read'}
 if kind=='publish':perms.update({'contents':'write','pull-requests':'write','actions':'read'})
 j={'needs':needs or [previous], 'if':condition or guard(previous), 'uses':f'./.github/workflows/autose-{kind}.yml',
    'permissions':perms, 'with':{'phase':phase,'prefix':name,'prior':pattern or previous,'base_sha':'${{ needs.admission.outputs.base_sha }}'}}
 if 'admission' not in j['needs']: j['needs'].append('admission')
 if kind=='broker':j['secrets']={'AUTOSE_MODEL_API_KEY':'${{ secrets.AUTOSE_MODEL_API_KEY }}'}
 jobs[name]=j
 return name

jobs['admission']={'runs-on':'ubuntu-latest','timeout-minutes':5,'permissions':{'contents':'read','pull-requests':'read'},
 'outputs':{k:'${{ steps.admit.outputs.'+k+' }}' for k in baseout},'steps':[
 {'uses':'actions/checkout@v4','with':{'ref':'${{ github.sha }}','fetch-depth':0,'persist-credentials':False}},
 {'uses':'actions/setup-python@v5','with':{'python-version':'3.12'}},
 {'id':'admit','env':{'PYTHONPATH':'workflow','GITHUB_TOKEN':'${{ github.token }}'},'run':'python -m autose.cli admission --output out'},
 {'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'admission-attempt-${{ github.run_attempt }}','path':'out/','if-no-files-found':'error','retention-days':90}}]}
last='admission'
for rnd in (1,2):
 if rnd==2:
  last=call('r2_start','repair',last,'data',condition=guard(last,'repair'))
 req=call(f'r{rnd}_requirements','requirements',last)
 des=call(f'r{rnd}_design','design',req)
 results=[]
 for att in (1,2):
  prefix=f'r{rnd}a{att}'
  start=des if att==1 else call(prefix+'_start','repair',results[-1],'data',condition=guard(results[-1],'retry'))
  impl=call(prefix+'_impl','implementation',start)
  build=call(prefix+'_build','compile',impl,'execute')
  author=call(prefix+'_author','author-tests',build)
  test=call(prefix+'_tests','tests',author,'execute')
  result=call(prefix+'_result','select',impl,'data',condition=f"always() && needs.{impl}.result == 'success'",needs=[impl,build,author,test],pattern=prefix+'_*')
  results.append(result)
 done=call(f'r{rnd}_done','select',results[0],'data',condition=f"always() && needs.{results[0]}.result == 'success'",needs=results,pattern=f'r{rnd}a*_result')
 rel=call(f'r{rnd}_release','release',done,'publish',condition=guard(done,'passed'))
 rev=call(f'r{rnd}_review','review',rel)
 rtest=call(f'r{rnd}_review_tests','review-tests',rev,'execute')
 rfinal=call(f'r{rnd}_review_final','review-final',rtest)
 last=call(f'r{rnd}_post','post-review',rfinal,'publish')
call('final_evidence','final',last,'data',condition="always() && needs.admission.result == 'success'",needs=list(jobs),pattern='*')
doc={'name':'AutoSE issue to independently reviewed PR','on':{'issues':{'types':['labeled']},'issue_comment':{'types':['created']}},
 'permissions':{},'concurrency':{'group':'autose-${{ github.repository }}-${{ github.event.issue.number }}','cancel-in-progress':False},'jobs':jobs}
(repo/'.github/workflows/autose.yml').write_text(yaml.safe_dump(doc,sort_keys=False,width=160))
ci={'name':'AutoSE exact-head CI','on':{'pull_request':{'branches':['main']}},'permissions':{'contents':'read'},'jobs':{
 'tinydb-tests':{'runs-on':'ubuntu-latest','timeout-minutes':10,'steps':[
  {'uses':'actions/checkout@v4','with':{'ref':'${{ github.event.pull_request.base.sha }}','path':'trusted','fetch-depth':0,'persist-credentials':False}},
  {'uses':'actions/checkout@v4','with':{'ref':'${{ github.event.pull_request.head.sha }}','path':'candidate','persist-credentials':False}},
  {'uses':'actions/setup-python@v5','with':{'python-version':'3.12'}},
  {'name':'Build trusted image','run':'docker build -t autose-pytest:trusted -f trusted/workflow/Dockerfile trusted/workflow'},
  {'name':'Test exact PR head in isolated container','env':{'PYTHONPATH':'trusted/workflow'},'run':'python trusted/workflow/ci_exact.py'},
  {'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'exact-head-test-evidence-attempt-${{ github.run_attempt }}','path':'ci-output/','retention-days':90}}]}}}
(repo/'.github/workflows/autose-ci.yml').write_text(yaml.safe_dump(ci,sort_keys=False,width=120))
for p in (repo/'.github/workflows').glob('autose*.yml'):shutil.copy2(p,repo/'workflow/workflows'/p.name)
print('Generated',len(jobs),'statically bounded jobs; secret only passed to broker jobs. New autose workflows mirrored.')
