"""Independent execution records. Only the isolated local supervisor authorizes.

Legacy signature parsing remains for archived protocol tests, not a production
signing-service fallback. Candidate output never supplies a verdict.
"""
import base64
from pathlib import Path
import subprocess
import tempfile
import time
import re

from .common import GateError, digest, encoded, json_load, require

DOMAIN=b'AUTOSE independent tests v1\n'


def environment_spec():
    from .authority_backend import POLICY,trusted_code_hash
    config=json_load(Path(__file__).resolve().parents[1]/'config/test-authority.json')
    return {'policy':POLICY,'controller_sha256':trusted_code_hash(),'image_digest':config.get('image_digest')}


def require_authoritative(result, expected_source=None):
    require(result.get('passed') is True and result.get('authoritative') is True,
            'independent test verification required; candidate reports are untrusted')
    record=result.get('verification',{}).get('record',{})
    require(record.get('identity')==result.get('identity') and record.get('completed') is True
            and record.get('verdict')=='passed','independent verification identity/result missing')
    require(type(record.get('expires_at')) in (int,float) and time.time()<record['expires_at'],'independent verification expired')
    require(record.get('schema')=='autose-isolated-authority-v2','isolated authority evidence required')
    env=record.get('environment',{})
    expected=result['identity'].get('expected_environment',{})
    require(all(env.get(k)==expected.get(k) for k in ('policy','controller_sha256','image_digest')),
            'verified execution environment mismatch')
    require(env.get('policy')=='autose-isolated-rpc-v1' and env.get('isolation')=='docker_candidate_private_namespace' and
            isinstance(env.get('image_digest'),str) and re.fullmatch('sha256:[a-f0-9]{64}',env['image_digest']),'verified isolation missing')
    if expected_source is not None:
        require(result.get('identity',{}).get('source_sha256')==expected_source,'verified source identity mismatch')


def validate_record(record, plan):
    require(isinstance(record,dict) and record.get('schema') in ('autose-independent-tests-v1','autose-isolated-authority-v2'),'invalid independent verdict')
    require(record.get('identity')==plan['identity'] and record.get('plan_sha256')==digest(encoded(plan)), 'independent execution identity mismatch')
    require(record.get('method')=='independent-baseline-and-generated-execution', 'candidate report/signing-only verification forbidden')
    require(record.get('completed') is True and record.get('verdict')=='passed','independent tests incomplete/failed')
    if record['schema']=='autose-isolated-authority-v2':
        expected=plan['identity'].get('expected_environment',{})
        require(isinstance(expected,dict) and set(expected)=={'policy','controller_sha256','image_digest'} and
                all(record.get('environment',{}).get(k)==v for k,v in expected.items()),'independent environment mismatch')
    now=time.time()
    require(type(record.get('completed_at')) in (int,float) and type(record.get('expires_at')) in (int,float)
            and now-3600 <= record['completed_at'] <= now < record['expires_at'] <= record['completed_at']+3600,'independent verdict stale/expired')
    require(isinstance(record.get('evidence_uri'),str) and record['evidence_uri'].startswith('https://'),'independent execution evidence missing')
    expected=set(map(tuple,plan['baseline_case_ids']))
    ids=[];run_ids=[]
    for name in ('baseline','generated'):
        suite=record.get(name)
        require(isinstance(suite,dict) and suite.get('completed') is True and suite.get('genuine_result')=='passed', 'independent suite incomplete/failed')
        require(type(suite.get('exit_status')) is int and suite['exit_status']==0 and
                all(type(suite.get(k)) is int and suite[k]==0 for k in ('failures','errors','skipped')), 'independent suite exit/result failed')
        require(isinstance(suite.get('execution_id'),str) and suite['execution_id'],'independent suite identity missing')
        run_ids.append(suite['execution_id'])
        cases=suite.get('case_ids')
        require(isinstance(cases,list) and all(isinstance(c,list) and len(c)==2 and all(isinstance(v,str) and v for v in c) for c in cases),'invalid independent case coverage')
        pairs=list(map(tuple,cases))
        require(len(pairs)==len(set(pairs)),'duplicate independent cases')
        require(type(suite.get('case_count')) is int and suite['case_count']==len(pairs),'independent case count mismatch')
        if name=='baseline':
            require(set(pairs)==expected,'complete baseline case coverage required')
        else:
            files=set(plan['generated_files'])
            require({c[0].replace('.','/')+'.py' for c in pairs}==files,'generated file coverage mismatch')
            for node in plan['test_map'].values():
                path,function=node.split('::')
                require(any(c==path[:-3].replace('/','.') and (n==function or n.startswith(function+'[')) for c,n in pairs),'mapped independent test missing')
        ids+=pairs
    require(run_ids[0]!=run_ids[1] and len(ids)==len(set(ids)),'independent suites must be separate executions')
    return ids


def verify_envelope(envelope, public_key_pem, plan):
    require(isinstance(envelope,dict) and isinstance(envelope.get('record'),dict),'independent signed record missing')
    require(isinstance(public_key_pem,str) and public_key_pem.startswith('-----BEGIN PUBLIC KEY-----'),'trusted verification public key missing')
    try:
        signature=base64.b64decode(envelope.get('signature',''),validate=True)
    except (ValueError,TypeError):
        raise GateError('invalid independent signature') from None
    require(len(signature)==64,'invalid independent Ed25519 signature length')
    with tempfile.TemporaryDirectory(prefix='autose-verify-') as directory:
        root=Path(directory)
        (root/'public.pem').write_text(public_key_pem)
        (root/'record').write_bytes(DOMAIN+encoded(envelope['record']).encode())
        (root/'signature').write_bytes(signature)
        try:
            result=subprocess.run(['openssl','pkeyutl','-verify','-pubin','-inkey',str(root/'public.pem'),
                '-rawin','-in',str(root/'record'),'-sigfile',str(root/'signature')],capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired):
            raise GateError('independent signature verifier unavailable') from None
        require(result.returncode==0,'independent signature rejected')
    ids=validate_record(envelope['record'],plan)
    return {'record':envelope['record'],'signature':envelope['signature'],'case_ids':ids,'verified':True}


def configured_authority(work_dir=None):
    path=Path(__file__).resolve().parents[1]/'config/test-authority.json'
    config=json_load(path)
    if config.get('backend','isolated-rpc-v1')=='isolated-rpc-v1':
        from .authority_backend import IsolatedAuthority
        require(work_dir is not None,'independent authority workspace missing')
        return IsolatedAuthority(config,work_dir)
    require(False,'signing-service fallback unsupported; isolated execution required')
