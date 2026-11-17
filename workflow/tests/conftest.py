import copy
import json
from pathlib import Path
import time
import sys

import pytest

from autose.common import PIN, REPOSITORY, ROLE_IDENTITY, budget, digest, encoded
from autose.contracts import DOC_HEADINGS
from autose.source import snapshot

REPO = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


@pytest.fixture(scope='session')
def baseline():
    return snapshot(REPO)


@pytest.fixture
def state(baseline):
    issue={'number':1,'title':'Duplicate removal','body':'Repeated IDs must remove each document once in requested order. Keep other tables and cache correct.'}
    return {'repository':REPOSITORY,'pin':PIN,'base_sha':'a'*40,'run_id':'1','event_id':'1','run_attempt':1,
        'attempt_id':'1-1','started_at':time.time(),'execution_kind':'local_fixture','issue':issue,
        'issue_hash':digest(encoded(issue)),'authorization':{'actor':'DineshThiraj','permission':'admin','scope':'exact explicit issue'},
        'baseline':copy.deepcopy(baseline),'source':copy.deepcopy(baseline),
        'limits':{'calls':24,'tokens':200000,'seconds':2400},'usage':{'calls':0,'tokens':0,'unknown':False},
        'round':1,'attempt':1,'route':'requirements','events':[],'gates':{}}


def specification(state):
    criteria=[]
    for n,quote in enumerate(('Repeated IDs must remove each document once in requested order.', 'Keep other tables and cache correct.'),1):
        criteria.append({'id':f'AC-{n:03}','requirement':f'FR-{n:03}','precondition':'A MemoryStorage or JSONStorage table with stored documents',
            'action':'Remove repeated IDs','expected':quote,'measurement':'pytest assertions on returned IDs and persisted state',
            'pass_fail':'Pass iff all stated outcomes hold','source_quote':quote,'evidence':'EXPLICIT','approval':'CONFIRMED'})
    docs={name:'\n\n'.join(h+'\nFixture-only analysis of '+state['issue']['body'] for h in headings)+'\n' for name,headings in DOC_HEADINGS.items()}
    return {'status':'READY','questions':[],'documents':docs,'criteria':criteria}


def plan():
    return {'design.md':'Fix Table.remove duplicate requested IDs before updater; preserve storage protocol and cache invalidation.',
        'targets':[{'path':'tinydb/table.py','function':'remove','new':False}],
        'coverage':{'AC-001':[0],'AC-002':[0]},'constraints':{str(i):'Preserve the verified A2 contract; fixture assessment.' for i in range(1,6)}}


TESTS = '''from tinydb import Query

def test_repeated_ids(db):
    table = db.table('targets')
    one, two, three = table.insert_multiple([{'value': 1}, {'value': 2}, {'value': 3}])
    assert table.remove(doc_ids=[two, one, two, 99999]) == [two, one]
    assert [d.doc_id for d in table.all()] == [three]

def test_preserve_tables_and_cache(db):
    table = db.table('targets')
    one, two = table.insert_multiple([{'value': 1}, {'value': 2}])
    query = Query().value > 0
    assert len(table.search(query)) == 2
    assert table.remove(doc_ids=[one, one]) == [one]
    assert [d.doc_id for d in table.search(query)] == [two]
    assert len(db) == 3
'''


class FixtureBroker:
    """No network, tokens or live model. Responses are test fixtures only."""
    def __init__(self, *, broken_first=False, reject_first=False, vague=False):
        self.requests=[]
        self.broken_first,self.reject_first,self.vague=broken_first,reject_first,vague

    def ask(self,state,role,instruction,context):
        budget(state)
        state['usage']['calls'] += 1
        self.requests.append((role,copy.deepcopy(context)))
        state.setdefault('calls',[]).append({'role':ROLE_IDENTITY[role],'stage':role,'fixture':True,'reported_tokens':None})
        if 'artifact' in context:
            return {'pass':True,'unsupported_scope':False,'evidence':'Fixture semantic response, not actual model validation.'}
        if role=='requirements':
            result=specification(state)
            if self.vague:result.update(status='needs_clarification',questions=['Which refresh/cache behavior is authorized?'])
            return result
        if role=='design':return plan()
        if role=='implementation':
            source=state['source']['tinydb/table.py']
            if not self.broken_first or state['attempt']==2 or state['round']==2:
                source=source.replace('requested_ids = list(doc_ids)','requested_ids = list(dict.fromkeys(doc_ids))')
            else:source += '\n# Deliberately ineffective fixture change.\n'
            return {'files':{'tinydb/table.py':source}}
        if role=='testing':return {'files':{'tests/test_autose_remove.py':TESTS},'test_map':{
            'AC-001':'tests/test_autose_remove.py::test_repeated_ids',
            'AC-002':'tests/test_autose_remove.py::test_preserve_tables_and_cache'}}
        if role=='review':
            if self.reject_first and state['round']==1:
                return {'verdict':'REQUEST_CHANGES','summary':'Fixture rejection for routing test; not a real finding.',
                    'run_tests':False,'findings':[{'path':'tinydb/table.py','line':1,'stage':'design','evidence':'Fixture-only requested design reconsideration.'}]}
            return {'verdict':'APPROVE','summary':'Fixture verdict; no actual independent model used.','run_tests':False,'findings':[]}
        raise AssertionError(role)


class FixturePublisher:
    """Local integration boundary double; never creates a GitHub object."""
    def publish(self,state):
        state['publication']={'number':1,'url':'fixture://not-a-github-pr/1','head_sha':'b'*40,'tree_sha':'c'*40}
    def ci(self,publication):return {'status':'passed','source':'fixture CI response; no hosted check'}
    def post_review(self,state):return {'url':'fixture://not-a-github-review/1','event':'APPROVE','github_approved':True}


@pytest.fixture
def baseline_ids():
    return json.loads((REPO/'workflow/config/baseline-case-ids.json').read_text())
