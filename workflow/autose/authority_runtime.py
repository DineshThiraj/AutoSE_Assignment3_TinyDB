"""Trusted pytest harness: imports baseline only; generated code is interpreted data."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import resource
import hashlib

import authority_bridge as bridge
from authority_dsl import check, Evaluator

def main():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    parser=argparse.ArgumentParser()
    parser.add_argument('--control',required=True)
    args=parser.parse_args()
    config=json.loads(Path(args.control).read_text())
    root=Path(config['tests_root'])
    import authority_fs
    authority_fs.install(config['scratch'])
    process=subprocess.Popen(config['worker_argv'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=open(config['worker_log'],'wb'),cwd=config['worker_cwd'],env=config['worker_env'],bufsize=0)
    session=bridge.Session(process,config['scratch'])
    bridge.install(session,root)
    import pytest
    import types
    class Generated(pytest.Module):
        def _getobj(self):
            path=Path(str(self.path))
            imports,functions=check(path.read_text())
            module=types.ModuleType(self.name);module.__file__=str(path)
            symbols={name:getattr(sys.modules[mod],symbol) for name,(mod,symbol) in imports.items()}
            for function in functions:
                def build(node):
                    def test(db):Evaluator({**symbols,'db':db}).run(node)
                    test.__name__=node.name;test.__qualname__=node.name;test.__module__=module.__name__
                    return test
                setattr(module,function.name,build(function))
            return module
    class Plugin:
        def __init__(self):self.collected=[];self.phases={};self.invalid=False
        def pytest_collection_modifyitems(self,items):
            self.collected=[item.nodeid for item in items]
            if len(self.collected)!=len(set(self.collected)):self.invalid=True
        def pytest_runtest_logreport(self,report):
            if report.nodeid not in self.collected or report.when not in ('setup','call','teardown'):
                self.invalid=True;return
            entry=self.phases.setdefault(report.nodeid,{})
            if report.when in entry:self.invalid=True
            entry[report.when]=report.outcome
        def pytest_pycollect_makemodule(self,module_path,parent):
            if Path(str(module_path)).name.startswith('test_autose_'):
                return Generated.from_parent(parent,path=module_path)
    code=None;plugin=Plugin()
    try:
        code=pytest.main(['-c','/dev/null','--rootdir='+str(root),'-o','addopts=','-p','no:cacheprovider',
            '--basetemp='+str(Path(config['scratch'])/'pytest'),'--junitxml='+config['report'],
            *config['test_paths']],plugins=[plugin])
    finally:
        worker_status=session.close()
        report=Path(config['report'])
        Path(config['completion']).write_text(json.dumps({'completed':code is not None,
            'identity':config['identity'],'suite':config['suite'],'environment_sha256':config['environment_sha256'],
            'exit_status':None if code is None else int(code),'protocol_failed':session.poisoned,
            'filesystem_failed':authority_fs.VIOLATIONS!=0,
            'collection_failed':plugin.invalid,'collected':plugin.collected,'phases':plugin.phases,
            'bridge_requests':session.seq,
            **worker_status,
            'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest() if report.is_file() else None}))
    return code

if __name__=='__main__':raise SystemExit(main())
