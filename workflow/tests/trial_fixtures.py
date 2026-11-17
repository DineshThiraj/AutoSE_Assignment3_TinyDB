"""Inert D6 contract fixtures. NO account evidence, authorization or network access."""
import base64
import copy
import hashlib
import threading
import time

from autose.common import REPOSITORY, digest, encoded
from autose.github import APIError
from autose.trial import INPUT_CEILING, MODEL, PRICING, issue_scope_hash, approval_scope_hash


def prepare_state(state):
    state['execution_kind'] = 'hosted'  # Only used with the in-memory GitHub/HTTP doubles.
    state['issue']['number'] = 3
    state['issue_hash'] = digest(encoded(state['issue']))
    state['trigger'] = {'kind':'issue_comment','actor':'DineshThiraj','comment_id':123}
    state['limits'].update(calls=8,tokens=8*(INPUT_CEILING+100))
    return state


def config(state):
    now = time.time()
    proof = {'verified':True,'project_id':'TEST-ONLY-NO-PROJECT','locator':'fixture://not-provider-evidence',
             'sha256':'e'*64,'checked_at':now-1,'expires_at':now+3600}
    trial = {'id':'test-only-approval','repository':REPOSITORY,'issue':3,'issue_hash':issue_scope_hash(state['issue']),
             'actor':'DineshThiraj','approved_by':'DineshThiraj','trigger_not_before':now-60,
             'project_id':proof['project_id'],'currency':'USD','max_usd':'100','max_calls':8,
             'max_tokens':state['limits']['tokens'],'expires_at':now+1000,
             **{key:copy.deepcopy(proof) for key in ('approval','provider_support','hard_cap','secret','pricing')}}
    trial['provider_support'].update(available=True,model=MODEL,endpoint='https://api.openai.com/v1/responses')
    trial['hard_cap'].update(enforced=True,currency='USD',limit_usd='100',remaining_usd='100',period_ends_at=now+4000)
    trial['secret'].update(available=True,name='AUTOSE_MODEL_API_KEY')
    trial['pricing']['schedule'] = PRICING
    result = {'enabled':True,'adapter':'openai-responses','model':MODEL,'effort':'medium','service_tier':'default',
            'token_budget':trial['max_tokens'],'max_output_tokens':100,'provider_support_evidence':'fixture only',
            'hard_cap_evidence':'fixture only','provider_cap_verified':True,'paid_authorized':True,
            'paid_authorization_evidence':'fixture only; NOT paid approval','authorization_expires_at':trial['expires_at'],'trial':trial}
    trial['approval']['scope_sha256'] = approval_scope_hash(result)
    return result


class MemoryGitHub:
    """REST Git Data contract double shared by independent clients; atomic ref creation.

    Object IDs are deterministic test identifiers. NOT evidence of hosted GitHub I/O.
    """
    def __init__(self):
        self.refs, self.objects, self.calls = {}, {}, []
        self.lock = threading.RLock()
        self.before_ref = None

    def repo(self, method, path, body=None):
        if method == 'POST' and path == '/git/refs' and self.before_ref:
            self.before_ref()
        with self.lock:
            self.calls.append((method,path,copy.deepcopy(body)))
            if method == 'POST' and path in ('/git/blobs','/git/trees','/git/commits'):
                value = copy.deepcopy(body)
                object_type = path.rsplit('/',1)[-1]
                data = (body['content'] if object_type == 'blobs' else encoded(body)).encode()
                raw = object_type.encode() + b' ' + str(len(data)).encode() + b'\0' + data
                key = hashlib.sha1(raw).hexdigest()
                if object_type == 'blobs':value = {'encoding':'base64','content':base64.b64encode(data).decode()}
                if object_type == 'commits':value['tree'] = {'sha':body['tree']}
                self.objects[key] = value
                return {'sha':key}
            if method == 'POST' and path == '/git/refs':
                if body['ref'] in self.refs:raise APIError(422)
                self.refs[body['ref']] = body['sha']
                return {'object':{'sha':body['sha']}}
            if method == 'GET' and path.startswith('/git/ref/'):
                key = 'refs/' + path[len('/git/ref/'):]
                if key not in self.refs:raise APIError(404)
                return {'object':{'sha':self.refs[key]}}
            if method == 'GET' and path.startswith(('/git/blobs/','/git/trees/','/git/commits/')):
                return copy.deepcopy(self.objects[path.rsplit('/',1)[-1]])
            raise AssertionError((method,path))
