# Evidence walkthrough · 4 minutes 36 seconds

[Recorded evidence walkthrough](../demo.mp4) uses real public GitHub captures and local result records, with synthesized narration. It is a truthful partial demonstration. A complete hosted issue-to-posted-review recording is unavailable.

## Scene-by-scene narration and capture plan

### 00:00–00:24 · Issue #3 · Duplicate removal

Show [https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/issues/3](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/issues/3). Public issue page captured 20 November 2026.

This is the TinyDB fork for Assignment Three. Issue three asks for duplicate document IDs to be safely removed once. I will show the architecture and real evidence available. The hosted issue-to-review workflow did not complete, so each observed run is identified separately.

### 00:24–00:53 · Five issues and a frozen oracle

Show [https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/issues](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/issues). Public issue list · five open issues.

The fork contains two bug reports, two feature requests, and a deliberately vague request about external updates. We froze nineteen private acceptance cases outside Git. The vague issue measures whether requirements stop for clarification. The whole-match regex reference conflicts with one original test.

### 00:53–01:22 · Four reasoning roles, six gated stages

Show [architecture/views/component-current.svg](../architecture/views/component-current.svg). Current component view · trusted tools and separated privileges.

The controller drives requirements, design, implementation, testing, release and independent review. The broker provides separate role contexts. The isolated executor never receives model or publisher credentials. The reviewer receives the issue, the exact-head source, the diff, and optional fixed test results. A trusted publisher posts the verdict. A human decides whether to merge.

### 01:22–01:52 · One real hosted issue event

Show [https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44069611603](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44069611603). Actions run 44069611603 · admission and finalization only.

This is the genuine issue-comment Actions run. Admission and final evidence completed as jobs. Thirty-nine downstream jobs were skipped. The green banner marks that limited workflow outcome. No hosted requirements, design, implementation, testing, release or reviewer stage ran, and there was no generated pull request.

### 01:52–02:22 · The bounded local fixture loop

Show [results/local-validation/summary.json](../results/local-validation/summary.json). Historical fixture artifacts · model and GitHub transport doubles.

The historical local fixture shows how the gate behaves after a bad proposal. Both attempts compile. Four new tests fail on attempt one. The bounded repair passes all two hundred thirty-two cases. The fixture also emits a spec, a design, a diff and a review record. Its apparent approval is a test double.

### 02:22–02:51 · Real Docker validation

Show [results/docker-observed.json](../results/docker-observed.json). Archived host run · 18 November · commit f6c727d.

This separate run used real local Docker and an independent supervisor. The positive candidate passed all two hundred twenty-eight baseline cases and four generated cases. The unfixed defect and forged verdict were rejected. Five containers were observed. The result establishes local behavior at the recorded revision.

### 02:51–03:20 · Two decision experiments

Show [experiment/variants.md](../experiment/variants.md). Measured local outcomes · no hosted treatment trials.

The first experiment compared candidate-reported test success with independent authority. A historical false pass motivated moving the verdict out of the candidate process. The second compared read-only grant checks with one-use consumption. Three concurrent copies reached a fake provider before the change. One did after it.

### 03:20–03:48 · Draft infrastructure PR #8

Show [https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/pull/8](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/pull/8). Public GitHub capture · infrastructure work.

This is the real draft infrastructure pull request, number eight. It is separate from the task issue and remains draft. The reviews API returned no reviews. Model-assisted security findings are recorded locally. They are separate from an independent reviewer-agent verdict posted to GitHub. Five seeded examples are also local, with accuracy unmeasured.

### 03:48–04:14 · Earlier hosted CI passed

Show [https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44280528872](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44280528872). Actions run 44280528872 · older base verifier.

Run forty-four two eight zero five two eight eight seven two passed its TinyDB check at the displayed head. GitHub used the earlier protected base verifier. The new protected dispatch, authority, and dedicated check issuer have no verified hosted deployment. A check on this infrastructure pull request does not establish completion of the issue workflow.

### 04:14–04:36 · Human merge authority

Show [results/local-validation/fixture-artifacts/MERGE_READINESS_CHECK.json](../results/local-validation/fixture-artifacts/MERGE_READINESS_CHECK.json). Actual local MERGE_READINESS_CHECK · fixture result.

The fixture readiness record says automated readiness false, human decision pending, and merge authorization false. Both production flags are disabled. Provider cap, secret, and total coordinator tokens remain unverified or unmeasured. The report separates the observed results from outstanding hosted work.

## Manual recording checklist

Use a clean public browser profile, hide notifications and terminal history, and close every private folder, token panel, and account settings tab. Capture only the named tabs or windows. Rehearse the scene durations, then export H.264 MP4 and verify it is at most 5:00. Keep the scope labels visible. Do not trigger the workflow, claim a posted review, or show private tests. The provided recording already covers this script with public captures and synthetic speech. For a replacement clip, place it at the repository root as `demo.mp4` or replace the README demo link with its verified public URL.

Read-only local and GitHub display commands:

```sh
cd ~/AutoSE_A3_work/repository
git log --oneline --reverse edff96a..HEAD
git status --short --branch
cat results/local-validation/summary.json
cat results/docker-observed.json
python3 -c 'import json; d=json.load(open("results/local-validation/fixture-artifacts/MERGE_READINESS_CHECK.json")); print({k:d[k] for k in ("execution_kind","automated_gates_satisfied","human_decision","merge_authorized")})'
gh run view 44069611603 --repo DineshThiraj/AutoSE_Assignment3_TinyDB --json jobs,url
gh run view 44280528872 --repo DineshThiraj/AutoSE_Assignment3_TinyDB --json conclusion,headSha,jobs,url
gh api repos/DineshThiraj/AutoSE_Assignment3_TinyDB/pulls/8/reviews --jq 'map({html_url,state})'
```

Optional controller test display with Python 3.12, pytest 9.2.0 and PyYAML 6.0.3 in the active environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:workflow \
  python -m pytest -c /dev/null -o addopts= -p no:cacheprovider -q workflow/tests tests
```
