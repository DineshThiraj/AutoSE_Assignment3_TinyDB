# Assignment 3 — TinyDB issue-to-reviewed-PR workflow

Fork: https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB

Upstream: msiemens/tinydb. Pinned source: `edff96aeb2616402e9489d46e90a592c05565621`.
Design-first commit: `67c9b3c4286f598d5d415fb60433870cf63035a8`, directly parented by that pin. It contains documentation/reuse only and precedes new workflow implementation. Original TinyDB source and tests are retained.

Status: local controller and fixture integration implemented; hosted execution, model configuration, protected-main setup, actual issues/PRs/reviews and experiments remain pending. This is not a completed submission. See `results/runs.md` for genuine hosted evidence; local fixture results are kept separately. No report, demonstration or final submission file is claimed.

The student supplied nine accepted architecture choices and deferred exact provider/model/effort in D6. Read `architecture/STUDENT_REVIEW.md`, the ten Nygard records and initial views. The proposed sequence is not a real-run sequence.

## Workflow and gates

`.github/workflows/autose.yml` starts on an authorized maintainer's `autose` label or exact `/autose` issue comment. PR comments, bots, outsiders, duplicate issue PRs, unknown permissions and missing setup evidence stop before model calls. The trusted controller freezes the issue/source and enforces the six stages. Publication is restricted to this fork, never main/upstream. The workflow has no merge operation.

| Stage | Artifact | Gate |
| --- | --- | --- |
| Requirements | spec.md + all three original A1 documents | Explicit-scope readiness, structured testable ACs and semantic validation; critical ambiguity stops needs_clarification |
| Design | design.md | Actual files/functions, every AC mapped, five A2 constraints assessed |
| Implementation | diff.patch + compile log | Allowlisted regular-file edits and fixed compile success |
| Testing | test_report.md + JUnit | Added asserted test per AC; all 228 original identifiers retained and original/new tests pass |
| Release | pr.md + actual PR/CI URLs | Open fork PR and successful trusted CI at its exact head SHA |
| Independent Review | review.md + posted review URL | Fresh restricted context; actual posted review; approval or terminal two-round exhaustion |

Four fresh reasoning roles use inert bounded source inputs. Only the broker sees a provider key. Target code runs in disposable no-secret/no-network containers; only a trusted publisher has repository write authority. The reviewer receives issue/diff/latest source and its own optional fixed-test result, with no edit/push tools or implementation reasoning. See `workflow/README.md` for exact commands, budgets, recovery and limitations.

## Hosted prerequisites — currently unresolved

Enable Issues; bootstrap main from the preserved reviewed lineage; configure actual PR/check/no-force/no-delete/no-bypass rules; enable the necessary Actions settings. Verify current actor permissions and GitHub token review/CI behavior. Do not reset master or force-push. Current administrative route and shell GitHub access are unavailable. See `workflow/SETUP_REQUIRED.md`.

No provider/model/effort is selected. The optional Responses adapter is implementation support only; it is not evidence that any model is available or any provider offers the required hard cap. `workflow/config/live.json` is disabled. Before enabling it, verify supported exact configuration and provider-enforced hard cap, configure `AUTOSE_MODEL_API_KEY` securely as a repository secret, and obtain separate explicit paid authorization with an amount and expiry. Configuration booleans alone do not verify external billing controls. Never paste secret values into chat.

## Local validation and AI assistance

Use Python 3.12 with pytest 9.2.0 and PyYAML 6.0.3. From this repository:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=workflow python -m pytest -c /dev/null -o addopts= -p no:cacheprovider workflow/tests
```

The integration test uses actual pinned TinyDB source and real compile/pytest processes. Model responses, publication, CI and reviews are deterministic test doubles, explicitly labelled fixtures. It deliberately fails an ineffective patch, then passes a bounded repair with 228 original plus four new test cases. These are not hosted Actions or independent model-review results.

Codex substantially assisted with source verification, planning, document formatting, diagrams, controller/workflow code, prompts, tests and debugging. Student choices/reasons are transcribed from the user's supplied review, retaining the original “suggested reason” labels; no independent claim of exclusive student authorship is made. Human review of the generated implementation remains pending. A1/A2 files are copied unchanged with provenance in `REUSE_RECORD.md`.
