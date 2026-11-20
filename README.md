# TinyDB issue-to-reviewed-PR workflow

**Autonomous Software Engineering Assignment 3 · 2025811002**

[Assignment fork](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB) of `msiemens/tinydb` at pin `edff96aeb2616402e9489d46e90a592c05565621`. The [design-first commit](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/commit/67c9b3c4286f598d5d415fb60433870cf63035a8) records the student-reviewed design. Agent implementation starts at `ba6fdaf`. Original TinyDB source and baseline tests are retained.

[Report (PDF)](report.pdf) · [Demo video (MP4)](demo.mp4) · [Demo script and capture plan](results/DEMO_SCRIPT.md) · [Results and run links](results/runs.md) · [Submission checklist](results/SUBMISSION_CHECKLIST.md)

## Architecture and stage checks

Four reasoning roles share six controlled SDLC stages. Requirements reuses the A1 skill. Design reuses the A2 architecture. The implementer proposes source and tests. A fresh reviewer sees the issue, exact-head source, diff and its own optional fixed-test result. It receives neither the implementation conversation nor write tools. The controller, not the model, controls transitions and retry limits. See the [component view](architecture/views/component-current.svg), [observed sequence](architecture/views/sequence-observed.md), [current stage map](architecture/views/stage-map-current.md), and [ADR summary](architecture/decisions/README.md).

| Stage | Artifact | Gate |
| --- | --- | --- |
| Requirements | `spec.md`, A1 documents | Explicit approval and testable criteria. Critical ambiguity stops for clarification. |
| Design | `design.md` | Real files and functions, every criterion mapped, A2 constraints checked. |
| Implementation | `diff.patch`, immutable candidate SHA | Allowlisted content and fixed compile command. |
| Testing | `test_report.md`, authority receipt | Independent execution checks 228 original test identifiers and generated coverage. A bounded repair may return to implementation. |
| Release | `pr.md`, PR and check identity | Exact candidate head and base, same-fork PR, required trusted CI. Missing or pending evidence blocks release. |
| Independent review | `review.md`, intended posted review evidence | Fresh context, bounded review rounds and revalidation at the posted head. Only a human can decide to merge. |

The broker alone receives the model key reference. Execution uses read-only GitHub access and isolated Docker; publisher and ledger writes are scoped to their functions. D6 defers selecting a deployed provider, model and reasoning effort. The scoped Responses adapter targets `gpt-6.1-sol` as a candidate and budgets calls, tokens and USD conservatively. Availability, deployment approval, the repository secret and a provider-enforced hard spending cap are **not verified**. Per-run usage would be recorded by the broker. No paid hosted model calls were observed and total tokens for coordinator AI assistance are **not measured**.

## Trigger and current operating status

The generic workflow listens for a maintainer-applied `autose` label or an issue comment. The paid trial guard in this branch accepts only the authorized maintainer’s exact comment `/autose` on issue **#3**, on attempt one and within an approved trial window. It rejects PR comments, labels for the paid trial, bots, unknown permissions, and replayed or already-published work. This documents the intended procedure after approved deployment. Keep both `workflow/config/live.json` and `workflow/config/test-authority.json` disabled for the submission.

The public fork has protected `main`, five open issues and an open draft [infrastructure PR #8](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/pull/8). [Hosted issue run 44069611603](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44069611603) ran admission and finalization only. [Hosted CI run 44280528872](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44280528872) passed under the older base verifier. The new protected verifier and dedicated check issuer have no verified hosted deployment. No issue-to-reviewed-PR run or posted reviewer-agent result was found. The draft infrastructure PR is outside issue-candidate scope.

A person must evaluate the exact PR head, verify testing and review evidence, and choose merge, revision, or close. Keep PR #8 in draft pending separately authorized infrastructure review. The controller has no merge operation. The [draft branch](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/tree/a3/d6-issue3-trial) contains the recorded Docker-tested source revision. [Known deployment and release limits](results/evidence_inventory.md).

## Reproduce local checks

Use Python 3.12, pytest 9.2.0 and PyYAML 6.0.3 from an existing trusted environment. From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=.:workflow \
  python -m pytest -c /dev/null -o addopts= -p no:cacheprovider -q workflow/tests tests
git diff --check
```

Recorded results are 316 controller and 228 TinyDB tests. The historical local flow exercises 232 real tests after a bounded repair using mocked model and GitHub boundaries. The recorded host Docker run independently accepted a positive candidate and rejected two negative cases under real containers. Its evidence is summarized in [Docker validation](results/docker-observed.json). [Private evaluation metadata](experiment/hidden_tests/README.md) describes the frozen corpus kept outside this repository. [Decision experiments](experiment/variants.md) compare local controls. Seeded reviewer examples are [local fixtures](experiment/seeded_prs/README.md) with no scored reviewer outcomes.

## AI assistance and student review

Codex substantially assisted with research and source verification, architecture drafting and formatting, controller/workflow code, prompts, tests, debugging, model-based security reviews, and the submission materials. The student’s original decisions and supplied reasoning are preserved in [STUDENT_REVIEW.md](architecture/STUDENT_REVIEW.md). The two retrospective records and this report synthesize evidence and require the student’s final review. Local model-based reviews do not count as external human audits or posted reviewer-agent results. A1 and A2 reuse provenance is in [REUSE_RECORD.md](REUSE_RECORD.md).
