"""Exercise the trusted runtime's real process and inherited resource limits."""

import json
import os
from pathlib import Path
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parents[1] / 'autose/authority_runtime.py'
SUPERVISOR_AS = 768 * 1024 * 1024
INITIAL_AS = 1024 * 1024 * 1024
ENV = {
    'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
    'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
}


def make_control(tmp_path):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    case = tmp_path / 'test_supervisor_limits.py'
    case.write_text(f"""import resource

def test_supervisor_limits():
    assert resource.getrlimit(resource.RLIMIT_AS) == ({SUPERVISOR_AS}, {SUPERVISOR_AS})
    assert resource.getrlimit(resource.RLIMIT_CPU) == (120, 120)
""")
    # A benign stand-in for the Docker CLI reads kernel limits after exec. It
    # waits for EOF, so the real runtime must close and reap it on success.
    worker = """
import json, resource, sys

limits = {name: resource.getrlimit(getattr(resource, name))
          for name in ('RLIMIT_AS', 'RLIMIT_CPU')}
print(json.dumps(limits), file=sys.stderr, flush=True)
assert sys.stdin.buffer.read() == b''
"""
    control = tmp_path / 'control.json'
    control.write_text(json.dumps({
        'worker_argv': [sys.executable, '-I', '-B', '-c', worker],
        'worker_cwd': str(tmp_path), 'worker_env': ENV,
        'worker_log': str(tmp_path / 'worker.log'), 'scratch': str(scratch),
        'tests_root': str(tmp_path), 'test_paths': [str(case)],
        'report': str(tmp_path / 'report.xml'), 'completion': str(tmp_path / 'completion.json'),
        'identity': {}, 'suite': 'baseline', 'environment_sha256': 'unit-test',
    }))
    return control


def test_supervisor_cap_stays_local_to_supervisor(tmp_path):
    control = make_control(tmp_path)
    launcher = """
import resource, runpy, sys
from pathlib import Path

runtime, initial = sys.argv[1:3]
sys.argv = [runtime, *sys.argv[3:]]
sys.path.insert(0, str(Path(runtime).parent))
resource.setrlimit(resource.RLIMIT_AS, (int(initial), int(initial)))
runpy.run_path(runtime, run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, '-I', '-B', '-c', launcher, str(RUNTIME),
         str(INITIAL_AS), '--control', str(control)],
        cwd=tmp_path, env=ENV, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    limits = json.loads((tmp_path / 'worker.log').read_text())
    assert limits == {'RLIMIT_AS': [INITIAL_AS, INITIAL_AS], 'RLIMIT_CPU': [120, 120]}
    completion = json.loads((tmp_path / 'completion.json').read_text())
    assert completion['phases'] == {
        'test_supervisor_limits.py::test_supervisor_limits': {
            'setup': 'passed', 'call': 'passed', 'teardown': 'passed',
        }
    }
    assert completion['worker_exit_status'] == 0
    assert completion['worker_timed_out'] is False


def test_failed_supervisor_cap_reaps_worker_without_starting_tests(tmp_path):
    control = make_control(tmp_path)
    launcher = """
import importlib
from pathlib import Path
import resource
import signal
import subprocess
import sys

runtime = Path(sys.argv.pop(1))
sys.path.insert(0, str(runtime.parent))
supervisor = importlib.import_module(runtime.stem)
setrlimit = resource.setrlimit
popen = subprocess.Popen
children = []
expected = OSError('test: supervisor address-space cap rejected')


def reject_cap(limit, values):
    if limit == resource.RLIMIT_AS:
        assert len(children) == 1
        raise expected
    setrlimit(limit, values)


def track_worker(*args, **kwargs):
    process = popen(*args, **kwargs)
    children.append(process)
    return process


resource.setrlimit = reject_cap
subprocess.Popen = track_worker
try:
    supervisor.main()
except OSError as error:
    assert error is expected
else:
    raise AssertionError('supervisor continued without its address-space cap')

child, = children
assert child.returncode == -signal.SIGKILL
assert child.stdin.closed and child.stdout.closed
assert 'pytest' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, '-I', '-B', '-c', launcher, str(RUNTIME), '--control', str(control)],
        cwd=tmp_path, env=ENV, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / 'completion.json').exists()
    assert not (tmp_path / 'report.xml').exists()
