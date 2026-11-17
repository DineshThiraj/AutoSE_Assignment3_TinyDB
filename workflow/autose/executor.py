"""Fixed execution commands. Hosted target code executes only inside Docker."""
from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import GateError, digest, require
from .source import materialize

COMPILE = """from pathlib import Path
for root in ('tinydb', 'tests'):
    for p in sorted(Path(root).rglob('*.py')):
        compile(p.read_bytes(), str(p), 'exec')
print('All source and test Python files compile')
"""
PYTEST = """import sys, pytest
sys.path.insert(0, '.')
raise SystemExit(pytest.main(['-c', '/dev/null', '--rootdir=.', '-o', 'addopts=', '-p', 'no:cacheprovider', '--junitxml=/out/junit.xml', 'tests']))
"""


def _limits():
    os.setsid()
    resource.setrlimit(resource.RLIMIT_FSIZE, (16_000_000, 16_000_000))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _run(argv, cwd, log, timeout, env):
    start = time.monotonic()
    timed_out = False
    with Path(log).open('wb') as stream:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=_limits)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
    return {"command": argv, "returncode": code, "timed_out": timed_out, "seconds": time.monotonic() - start,
            "log": Path(log).read_bytes()[:2_000_000].decode(errors='replace')}


def junit(path):
    p = Path(path)
    require(p.is_file() and not p.is_symlink() and p.stat().st_size < 2_000_000, "missing/invalid JUnit")
    root = ET.fromstring(p.read_bytes())
    cases = list(root.iter('testcase'))
    require(cases, "empty JUnit collection")
    require(not list(root.iter('error')) and not list(root.iter('failure')) and not list(root.iter('skipped')), "failed/skipped JUnit cases")
    ids = [(c.attrib.get('classname', ''), c.attrib['name']) for c in cases]
    require(len(set(ids)) == len(ids), "duplicate JUnit cases")
    # Detect non-testcase suite errors/collection failures, including empty failed suites.
    for suite in root.iter('testsuite'):
        require(all(int(suite.get(k, 0)) == 0 for k in ('errors', 'failures', 'skipped')), "suite failed/skipped")
    return ids


def execute(source, directory, *, phase, baseline_ids=(), test_map=None, local_fixture=False,
            python=sys.executable, timeout=300, image='autose-pytest:trusted'):
    require(phase in {'compile', 'testing'}, "execution phase")
    root = Path(directory).resolve()
    require(not root.exists(), "execution directory exists")
    root.mkdir(parents=True)
    target, output = root / 'source', root / 'output'
    materialize(source, target)
    output.mkdir()
    require(0 < timeout <= 300, "invalid execution timeout")
    env = {'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'LANG': 'C.UTF-8'}
    command = COMPILE if phase == 'compile' else PYTEST
    if local_fixture:
        require(os.environ.get('GITHUB_ACTIONS') != 'true', "local fixture execution forbidden on hosted runner")
        # This mode is ONLY for coordinator-authored fixtures; it is not a sandbox.
        command = command.replace('/out/junit.xml', str(output / 'junit.xml'))
        argv = [str(python), '-B', '-c', command]
    else:
        image_id = subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True,env=env).strip()
        require(image_id.startswith('sha256:'), 'trusted image identity missing')
        container_name = 'autose-' + digest(str(root))[:16]
        argv = ['docker', 'run', '--rm', '--name', container_name, '--network=none', '--read-only', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--pids-limit=128', '--memory=512m', '--cpus=2',
                '--ulimit', 'fsize=16000000:16000000', '--user', f'{os.getuid()}:{os.getgid()}',
                '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m', '-e', 'PYTHONDONTWRITEBYTECODE=1',
                '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1', '--mount', f'type=bind,src={target},dst=/work,readonly',
                '--mount', f'type=bind,src={output},dst=/out', '-w', '/work', image_id, 'python', '-B', '-c', command]
    try:
        result = _run(argv, target, root / 'execution.log', timeout, env)
    finally:
        if not local_fixture:
            subprocess.run(['docker','rm','-f',container_name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env,timeout=20)
    if not local_fixture:
        result['image_id'] = image_id
    result['isolation'] = 'local_fixture_unsandboxed' if local_fixture else 'docker_no_network_no_secrets'
    result['passed'] = result['returncode'] == 0 and not result['timed_out']
    xml_path = output / 'junit.xml'
    if phase == 'testing' and xml_path.is_file() and not xml_path.is_symlink() and xml_path.stat().st_size < 2_000_000:
        result['junit_xml'] = xml_path.read_text()
    if phase == 'testing' and result['passed']:
        try:
            ids = junit(output / 'junit.xml')
            require(set(map(tuple, baseline_ids)) <= set(ids), "original baseline cases missing")
            for node in (test_map or {}).values():
                path, function = node.split('::')
                classname = path[:-3].replace('/', '.')
                require(any(c == classname and (n == function or n.startswith(function + '[')) for c, n in ids), "mapped AC test not collected")
            result['case_ids'] = ids
            result['case_count'] = len(ids)
            result['baseline_cases'] = len(baseline_ids)
            result['new_cases'] = len(ids) - len(baseline_ids)
        except (GateError, ET.ParseError) as error:
            result.update(passed=False, validation_error=str(error))
    return result
