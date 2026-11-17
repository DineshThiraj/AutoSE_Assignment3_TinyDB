"""One trusted phase per job. Artifact errors stop; no model-supplied commands."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import engine
from .broker import ResponsesBroker
from .common import GateError, STAGES, artifact, digest, encoded, gate, json_load, load_artifact, readiness, require
from .executor import execute
from .github import GitHub


ROLE_PHASES = {'requirements','design','implementation','author-tests','review','review-final'}
PHASE_STAGE = {'author-tests':'testing','compile':'implementation','tests':'testing',
               'review-tests':'review','review-final':'review','post-review':'review'}


def outputs(state):
    failed_execution = any(state.get('gates', {}).get(s, {}).get('status') == 'failed' for s in ('implementation','testing'))
    last_stage = PHASE_STAGE.get(state.get('phase'), state.get('phase'))
    status = state.get('gates', {}).get(last_stage, {}).get('status')
    return {
        'ready':not state.get('fatal') and status not in {'failed','needs_clarification','pending','exhausted'},
        'passed':state.get('gates', {}).get('testing', {}).get('status') == 'passed' and not state.get('fatal'),
        'retry':failed_execution and state.get('attempt') == 1 and not state.get('fatal'),
        'repair':state.get('gates', {}).get('review', {}).get('status') == 'failed' and state.get('round') == 1 and not state.get('fatal'),
        'want_tests':state.get('review_requested_tests',False),
        'base_sha':state.get('base_sha',''),
    }


def render(state):
    result = {'gate.json':encoded({'gates':state.get('gates',{}),'fatal':state.get('fatal'), 'phase':state.get('phase')}) + '\n'}
    if 'spec' in state:
        from .contracts import DOC_HEADINGS
        docs = state['spec'].get('documents', {})
        if isinstance(docs, dict):
            result.update({k:v for k,v in docs.items() if k in DOC_HEADINGS and isinstance(v,str) and v})
        if 'requirements_spec.md' in result:
            result['spec.md'] = result['requirements_spec.md']
    if 'design' in state and isinstance(state['design'].get('design.md'), str):
        result['design.md'] = state['design']['design.md']
    if 'patch' in state:
        result['diff.patch'] = state['patch']
    if 'execution' in state:
        result['execution.log'] = state['execution']['log'] or 'No process output.\n'
        result['test_report.md'] = '# Test report\n\n' + encoded({k:v for k,v in state['execution'].items() if k not in {'log','junit_xml'}}) + '\n\nAC mapping: ' + encoded(state.get('test_map',{})) + '\n'
        if state['execution'].get('junit_xml'):
            result['junit.xml'] = state['execution']['junit_xml']
    if 'publication' in state:
        result['pr.md'] = '# Release\n\n' + encoded(state['publication']) + '\n'
    if 'review' in state:
        result['review.md'] = '# Independent review\n\n' + encoded(state['review']) + '\n\nPosted review: ' + encoded(state.get('posted_review',{})) + '\n'
    if state.get('fatal'):
        stage = PHASE_STAGE.get(state.get('phase'), state.get('phase'))
        filename = {'requirements':'spec.md','design':'design.md','implementation':'implementation.md',
                    'testing':'test_report.md','release':'pr.md','review':'review.md'}.get(stage,'admission.md')
        result.setdefault(filename, '# Stage stopped\n\n' + state['fatal'] + '\n')
    result['MERGE_READINESS_CHECK.json'] = encoded(readiness(state)) + '\n'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['admission','requirements','design','implementation','compile','author-tests',
                        'tests','release','review','review-tests','review-final','post-review','repair','select','final'])
    parser.add_argument('--input', default='input')
    parser.add_argument('--output', default='output')
    parser.add_argument('--repo', default='.')
    parser.add_argument('--work', default='execution')
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    state = None
    try:
        if args.phase == 'admission':
            event = json_load(os.environ['GITHUB_EVENT_PATH'])
            state = engine.admit(event, os.environ['GITHUB_EVENT_NAME'], GitHub(), repo,
                run_id=os.environ['GITHUB_RUN_ID'],run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
                config=json_load(repo/'workflow/config/live.json'))
            require(state['base_sha'] == os.environ['GITHUB_SHA'], 'trusted checkout no longer matches main')
        elif args.phase in {'select','final'}:
            candidates = [load_artifact(p.parent) for p in sorted(Path(args.input).glob('*/manifest.json'))]
            require(candidates, 'no input state artifacts')
            identities = {(s['repository'],s['attempt_id'],s['issue_hash']) for s in candidates}
            require(len(identities) == 1, 'mixed run/issue artifacts')
            state = max(candidates, key=lambda s:s.get('step_no',0))
        else:
            input_path = Path(args.input)
            if args.phase == 'repair' and not (input_path/'manifest.json').exists():
                manifests = list(input_path.glob('*/manifest.json'))
                require(len(manifests) == 1, 'ambiguous repair checkpoint')
                input_path = manifests[0].parent
            state = load_artifact(input_path)
            require(not state.get('fatal'), 'previous stage failed')
            broker = None
            skip = (args.phase == 'requirements' and state.get('route') != 'requirements') or (
                args.phase == 'design' and state.get('route') not in {'requirements','design'}) or (
                args.phase == 'implementation' and state.get('route') == 'testing' and state['attempt'] == 1) or (
                args.phase == 'review-final' and not state.get('review_requested_tests'))
            if args.phase in ROLE_PHASES and not skip:
                broker = ResponsesBroker(json_load(repo/'workflow/config/live.json'))
            if args.phase == 'requirements' and not skip:
                engine.requirements(state, broker, repo)
            elif args.phase == 'design' and not skip:
                engine.design(state, broker, repo)
            elif args.phase == 'implementation' and not skip:
                engine.implementation(state, broker, repo)
            elif args.phase == 'compile':
                engine.compile_stage(state, args.work)
            elif args.phase == 'author-tests':
                engine.author_tests(state, broker, repo)
            elif args.phase == 'tests':
                engine.test_stage(state, args.work,baseline_ids=json_load(repo/'workflow/config/baseline-case-ids.json'))
            elif args.phase == 'release':
                engine.release(state, GitHub())
            elif args.phase == 'review':
                engine.independent_review(state, broker, repo)
            elif args.phase == 'review-tests' and state.get('review_requested_tests'):
                result = execute(state['source'],args.work,phase='testing',
                    baseline_ids=json_load(repo/'workflow/config/baseline-case-ids.json'),test_map=state['test_map'],timeout=min(300,engine.remaining(state)))
                state['own_review_execution'] = result
            elif args.phase == 'review-final' and not skip:
                engine.independent_review(state,broker,repo,own_test_result=state['own_review_execution'])
            elif args.phase == 'post-review':
                engine.publish_review(state, GitHub())
            elif args.phase == 'repair':
                if state.get('gates',{}).get('review',{}).get('status') == 'failed':
                    engine.repair(state)
                else:
                    engine.retry(state)
    except Exception as error:
        # Avoid printing tracebacks/provider bodies/headers or arbitrary model values.
        # GateError messages are controller-authored; other exceptions get a type only.
        message = str(error) if isinstance(error, GateError) else 'Internal phase error: ' + type(error).__name__
        if state is None:
            from .common import PIN, REPOSITORY
            state = {'repository':REPOSITORY,'pin':PIN,'issue':{},'issue_hash':digest(encoded({})),
                'execution_kind':'hosted','attempt_id':os.environ.get('GITHUB_RUN_ID','unknown'),
                'gates':{},'events':[]}
        state['fatal'] = message
        stage = PHASE_STAGE.get(args.phase,args.phase)
        if stage in STAGES or stage == 'admission':
            gate(state,stage,'failed',message)
    state['phase'] = args.phase
    state['step_no'] = state.get('step_no',0)+1
    artifact(args.output,state,render(state))
    selected = outputs(state)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
            for name,value in selected.items():
                stream.write(name+'='+ (str(value).lower() if isinstance(value,bool) else value)+'\n')
    print(encoded({'phase':args.phase,'fatal':state.get('fatal'),**selected}))
    # Failed gate states are artifacts/outputs, not lost exceptions. Workflow jobs
    # check ready/passed/repair; no downstream phase treats process exit as its gate.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
