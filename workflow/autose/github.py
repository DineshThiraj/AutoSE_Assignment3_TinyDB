"""Fork-scoped API publisher. Never imports or executes target source."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .common import GateError, PIN, REPOSITORY, digest, encoded, require, sha


class APIError(GateError):
    def __init__(self, status):
        super().__init__(f'GitHub request failed ({status}); no automatic mutation retry')
        self.status = status


class GitHub:
    def __init__(self, token=None, transport=None):
        self.token = token if token is not None else os.environ.get('GITHUB_TOKEN', '')
        self.transport = transport

    def call(self, method, path, body=None):
        require(method in {'GET', 'POST', 'PATCH'}, 'unsupported GitHub method')
        require(path.startswith('/') and '..' not in path and '\\' not in path, 'unsafe GitHub path')
        if self.transport:
            return self.transport(method, path, body)
        require(self.token, 'GitHub token unavailable')
        req = urllib.request.Request('https://api.github.com' + path,
            data=None if body is None else encoded(body).encode(), method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
                raw = response.read(4_000_001)
        except urllib.error.HTTPError as error:
            raise APIError(error.code) from None
        except urllib.error.URLError:
            raise APIError('network') from None
        require(len(raw) <= 4_000_000, 'GitHub response too large')
        return json.loads(raw)

    def repo(self, method, path='', body=None):
        require(path == '' or path.startswith('/'), 'repository API path')
        if method != 'GET':
            self.verify_repository()
        return self.call(method, '/repos/' + REPOSITORY + path, body)

    def verify_repository(self):
        info = self.call('GET', '/repos/' + REPOSITORY)
        require(info.get('id') == 1461061397 and info.get('full_name') == REPOSITORY, 'repository identity mismatch')
        require(info.get('fork') is True and info.get('parent', {}).get('full_name') == 'msiemens/tinydb', 'fork provenance mismatch')
        require(info.get('owner', {}).get('login') == 'DineshThiraj' and not info.get('archived'), 'repository not eligible')
        return info

    def pages(self, path, *, collection=None):
        values = []
        for page in range(1, 101):
            sep = '&' if '?' in path else '?'
            data = self.repo('GET', f'{path}{sep}per_page=100&page={page}')
            batch = data[collection] if collection else data
            require(isinstance(batch, list), 'GitHub pagination schema')
            values.extend(batch)
            if len(batch) < 100:
                return values
        raise GateError('GitHub pagination bound exhausted')

    def issue_prs(self, number):
        return self.pages('/pulls?' + urllib.parse.urlencode({'state':'all', 'head':f'DineshThiraj:autose/issue-{number}'}))

    def verify_rules_preflight(self, record):
        """Read effective rules without granting the workflow administration access.

        GitHub hides bypass actors from readers lacking ruleset write access. An
        independently verified, short-lived setup record is consequently required;
        its boolean is an attestation, not a claim to query invisible settings.
        """
        require(record.get('verified') is True and record.get('no_bypass_verified') is True, 'administrative protection verification missing')
        require(record.get('repository') == REPOSITORY and record.get('evidence'), 'protection verification origin/evidence missing')
        now = time.time()
        verified, expires = record.get('verified_at',0),record.get('expires_at',0)
        require(isinstance(verified,(int,float)) and isinstance(expires,(int,float)) and verified <= now < expires <= verified+86400, 'protection verification expired/invalid')
        rules = self.pages('/rules/branches/main')
        require(digest(encoded(rules)) == record.get('effective_rules_sha256'), 'effective branch rules changed')
        types = {r['type'] for r in rules}
        require({'pull_request','required_status_checks','non_fast_forward','deletion'} <= types, 'enforced PR/check/force/deletion rules missing')
        check_rules = [r.get('parameters',{}) for r in rules if r['type']=='required_status_checks']
        require(any(any(c.get('context')=='tinydb-tests' for c in r.get('required_status_checks',[])) for r in check_rules), 'required CI rule absent')
        return {'method':'effective_rules_plus_verified_admin_preflight','rules':rules,'setup_evidence':record['evidence'],
                'limitation':'Bypass actors are not visible to this token; separately verified setup record expires within 24h.'}

    def publish(self, state):
        from .common import passed
        passed(state, 'testing')
        require(state['execution_kind'] == 'hosted', 'fixture execution cannot publish')
        require(state['repository'] == REPOSITORY, 'state repository mismatch')
        base_sha = sha(state['base_sha'])
        current = self.repo('GET', '/git/ref/heads/main')['object']['sha']
        require(current == base_sha, 'base changed; rerun admission/design/tests')
        tree = self.repo('GET', '/git/trees/' + base_sha + '?recursive=1')
        require(tree.get('truncated') is False, 'base tree truncated')
        entries = {item['path']: item for item in tree['tree']}
        # Never overwrite a source baseline different from the one that was tested.
        def blob_sha(content):
            raw = content.encode()
            return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        for path, content in state['baseline'].items():
            require(entries.get(path, {}).get('sha') == blob_sha(content), 'base TinyDB differs from pinned source')
            require(entries[path]['mode'] == '100644' and entries[path]['type'] == 'blob', 'base source is not regular file')
        from .source import allowed, source_hash
        require(source_hash(state['source']) == state['tested_source_hash'], 'tested source identity changed')
        edits = []
        for path, content in state['source'].items():
            if state['baseline'].get(path) == content:
                continue
            allowed(path, 'implementation' if path.startswith('tinydb/') else 'testing')
            blob = self.repo('POST', '/git/blobs', {'content':content, 'encoding':'utf-8'})
            require(blob['sha'] == blob_sha(content), 'published blob mismatch')
            edits.append({'path':path, 'mode':'100644', 'type':'blob', 'sha':blob['sha']})
        require(edits, 'empty proposed change')
        new_tree = self.repo('POST', '/git/trees', {'base_tree':tree['sha'], 'tree':edits})['sha']
        branch = f"autose/issue-{state['issue']['number']}"
        prs = self.issue_prs(state['issue']['number'])
        require(len(prs) <= 1, 'multiple PRs for issue branch')
        existing = None
        try:
            existing = self.repo('GET', '/git/ref/heads/' + branch)['object']['sha']
        except APIError as error:
            require(error.status == 404, 'branch lookup unavailable')
        if existing:
            existing_commit = self.repo('GET', '/git/commits/' + sha(existing))
            require(prs and prs[0]['state'] == 'open' and prs[0]['base']['ref'] == 'main', 'existing branch needs manual reconciliation')
            require('<!-- autose-issue:' + str(state['issue']['number']) + ' -->' in (prs[0].get('body') or ''), 'unowned issue branch')
            require(prs[0]['head']['sha'] == existing, 'branch/PR head mismatch')
            expected = state.get('publication', {}).get('head_sha')
            require(existing_commit['tree']['sha'] == new_tree or expected == existing, 'branch head changed outside this attempt')
        parent = existing or base_sha
        if existing and existing_commit['tree']['sha'] == new_tree:
            head = existing
        else:
            commit = self.repo('POST', '/git/commits', {
                'message':f"autose: issue {state['issue']['number']} (run {state['run_id']})",
                'tree':new_tree, 'parents':[parent]})
            head = sha(commit['sha'])
            if existing:
                require(self.repo('GET', '/git/ref/heads/' + branch)['object']['sha'] == existing, 'branch raced publication')
                self.repo('PATCH', '/git/refs/heads/' + branch, {'sha':head,'force':False})
            else:
                self.repo('POST', '/git/refs', {'ref':'refs/heads/' + branch,'sha':head})
        if not prs:
            marker = f"<!-- autose-issue:{state['issue']['number']} -->\n<!-- autose-event:{state['event_id']} -->"
            pr = self.repo('POST', '/pulls', {'title':f"Issue #{state['issue']['number']}: {state['issue']['title']}"[:240],
                'head':branch,'base':'main','body':marker + f"\n\nCloses #{state['issue']['number']}\n\nAutomated proposal. Human merge decision required.\nRun: https://github.com/{REPOSITORY}/actions/runs/{state['run_id']}"})
        else:
            pr = self.repo('GET', '/pulls/' + str(prs[0]['number']))
        require(pr['state'] == 'open' and pr['head']['sha'] == head, 'published PR/head mismatch')
        state['publication'] = {'number':pr['number'],'url':pr['html_url'],'head_sha':head,'tree_sha':new_tree,'branch':branch,'ci':'pending'}
        return state['publication']

    def ci(self, publication):
        head = sha(publication['head_sha'])
        pr = self.repo('GET', '/pulls/' + str(publication['number']))
        require(pr['state'] == 'open' and pr['head']['sha'] == head and pr['base']['ref'] == 'main', 'PR identity/head changed')
        require(pr['head']['repo']['full_name'] == REPOSITORY and pr['base']['repo']['full_name'] == REPOSITORY, 'cross-repository PR')
        runs = self.pages('/actions/workflows/autose-ci.yml/runs?' + urllib.parse.urlencode({'head_sha':head, 'event':'pull_request'}), collection='workflow_runs')
        runs = [r for r in runs if r['head_sha'] == head and r['event'] == 'pull_request' and r.get('path') == '.github/workflows/autose-ci.yml']
        if not runs:
            return {'status':'pending','reason':'No exact-head trusted PR CI run; token-created PR may need workflow approval.'}
        latest = max(runs, key=lambda r:(r['run_number'],r.get('run_attempt',1)))
        result = {'status':'pending','url':latest['html_url'],'head_sha':head}
        if latest['status'] != 'completed':
            return result
        jobs = self.pages('/actions/runs/' + str(latest['id']) + '/jobs?filter=latest', collection='jobs')
        require(latest['conclusion'] == 'success', 'exact-head CI failed')
        require(jobs and any(j['name'] == 'tinydb-tests' for j in jobs), 'required CI job absent')
        require(all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs), 'CI job skipped/pending/failed')
        result['status'] = 'passed'
        return result

    def post_review(self, state):
        publication, review = state['publication'], state['review']
        require(self.ci(publication)['status'] == 'passed', 'CI gate no longer current')
        body = f"Model verdict: {review['verdict']}\n\n{review['summary']}\n\n"
        body += '\n'.join(f"- {f['path']}:{f['line']} [{f['stage']}]: {f['evidence']}" for f in review['findings'])
        event = review['verdict']
        payload = {'commit_id':publication['head_sha'],'event':event,'body':body}
        try:
            posted = self.repo('POST', f"/pulls/{publication['number']}/reviews", payload)
        except APIError as error:
            if error.status != 422 or event not in {'APPROVE','REQUEST_CHANGES'}:
                raise
            # Preserve a real review and be explicit about platform self-approval limits.
            payload.update(event='COMMENT', body=body + f'\n\nGitHub {event} was rejected; this COMMENT records the model verdict without claiming a platform approval/change-request event.')
            posted = self.repo('POST', f"/pulls/{publication['number']}/reviews", payload)
        require(posted.get('commit_id') == publication['head_sha'], 'posted review commit mismatch')
        expected_state = {'APPROVE':'APPROVED','REQUEST_CHANGES':'CHANGES_REQUESTED','COMMENT':'COMMENTED'}[payload['event']]
        require(posted.get('state') == expected_state, 'posted review state mismatch')
        return {'url':posted['html_url'],'commit_id':posted['commit_id'],'event':payload['event'],
                'github_approved':posted['state'] == 'APPROVED'}

    def wait_ci(self, publication, *, seconds=300, interval=10):
        require(0 <= seconds <= 300 and 0 < interval <= 10, 'CI wait bound')
        deadline = time.monotonic() + seconds
        while True:
            result = self.ci(publication)
            if result['status'] == 'passed' or time.monotonic() >= deadline:
                return result
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
