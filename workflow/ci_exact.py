"""Run from reviewed BASE code; candidate files are read as inert text."""
import json
import os
from pathlib import Path
import subprocess

from autose.common import PIN, require
from autose.executor import execute
from autose.source import snapshot
from autose.verification import require_authoritative


def main():
    trusted = Path(__file__).resolve().parent.parent
    candidate = Path('candidate').resolve()
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    expected = event['pull_request']['head']['sha']
    actual = subprocess.check_output(['git','-C',str(candidate),'rev-parse','HEAD'],text=True).strip()
    require(actual == expected, 'CI candidate commit mismatch')
    baseline = snapshot(trusted)
    names = subprocess.check_output(['git','-C',str(candidate),'ls-tree','-r','--name-only',actual,'tinydb','tests'],text=True).splitlines()
    source = {}
    for name in names:
        if not name.endswith('.py'):
            continue
        mode = subprocess.check_output(['git','-C',str(candidate),'ls-tree',actual,'--',name],text=True).split()[0]
        require(mode == '100644', 'non-regular candidate source')
        raw = subprocess.check_output(['git','-C',str(candidate),'show',actual+':'+name])
        require(len(raw) <= 150_000, 'candidate file too large')
        source[name] = raw.decode()
    for path,value in baseline.items():
        require(path in source, 'baseline file missing')
        if path.startswith('tests/'):
            require(value == source[path], 'original test changed')
    baseline_ids=json.loads((trusted/'workflow/config/baseline-case-ids.json').read_text())
    result=execute(source,'ci-output',phase='testing',baseline_ids=baseline_ids,head_sha=actual)
    result['head_sha']=actual
    Path('ci-output/result.json').write_text(json.dumps(result,indent=2)+'\n')
    require_authoritative(result)


if __name__ == '__main__':
    main()
