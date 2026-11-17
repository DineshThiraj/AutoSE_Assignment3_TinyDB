# Initial design coverage audit — 2026-11-17

Codex document audit, not a completed independent grading audit or runtime verification. All forty source requirements have been considered; architecture does not complete execution/report requirements. Nine complete accepted student choices (D1–D5, D7–D10), one deferred model record (D6), ten Nygard ADRs, six stage contracts, rendered component view and explicitly proposed sequence are present. A1/A2 reuse is unchanged. No agent implementation or new workflow has been written. Existing upstream workflows remain untouched.

| Assignment requirement | Intended evidence | Design audit status |
| --- | --- | --- |
| R01 [front matter] Deadline 2026-11-21 23:59 IST (18:29 UTC); extension only if requested before deadline, 3 days total across assignments | evidence/source/verification.json | COVERED IN PLAN; execution/submission evidence pending |
| R02 [Mission] Hosted Actions workflow in .github/workflows triggered by maintainer label or comment | repository/.github/workflows/autose.yml; results/runs.md | COVERED IN PLAN; execution/submission evidence pending |
| R03 [six-stage table] Requirements: Reuse actual A1 skill; artifact spec.md; gate: All criteria testable | results/<run>/spec.md | COVERED IN PLAN; execution/submission evidence pending |
| R04 [six-stage table] Design: Use actual A2 ARCHITECTURE.md; artifact design.md; gate: Names actual files and functions | results/<run>/design.md | COVERED IN PLAN; execution/submission evidence pending |
| R05 [six-stage table] Implementation: New branch following design; artifact diff.patch; gate: Code builds | results/<run>/diff.patch | COVERED IN PLAN; execution/submission evidence pending |
| R06 [six-stage table] Testing: Write a test per criterion; failing tests return to implementation; artifact test_report.md; gate: New and all existing tests pass | results/<run>/test_report.md | COVERED IN PLAN; execution/submission evidence pending |
| R07 [six-stage table] Release: Push branch; save real PR link; artifact pr.md; gate: Open PR and CI passes | results/<run>/pr.md | COVERED IN PLAN; execution/submission evidence pending |
| R08 [six-stage table] Review: Separate reviewer; route fixes to relevant earlier stage, bounded at two; artifact review.md; gate: Approval or two review rounds exhausted | results/<run>/review.md | COVERED IN PLAN; execution/submission evidence pending |
| R09 [stage failure] Unpassed gate explains failure in its artifact and stops; bounded earlier-stage returns | results/<run>/events.jsonl; stage artifacts | COVERED IN PLAN; execution/submission evidence pending |
| R10 [independence] Reviewer sees only issue, diff, latest PR checkout; separate prompt; read/run permission, no push; no implementer reasoning | review prompt; permission policy; review input manifest | COVERED IN PLAN; execution/submission evidence pending |
| R11 [architecture] Human alone decides final merge; workflow never merges | workflow permissions; PR status | COVERED IN PLAN; execution/submission evidence pending |
| R12 [Decisions] At least 8 ADRs from D1–D10 in Nygard format; concrete alternatives and consequences | architecture/decisions/ | INITIAL DESIGN CHECKED; runtime evidence pending |
| R13 [architecture views] Component view: agents, tools and calls | architecture/views/component.dot; component.svg | INITIAL DESIGN CHECKED; runtime evidence pending |
| R14 [architecture views] Sequence view of one REAL run trigger through review | architecture/views/sequence-real-run.* | PROPOSED VIEW ONLY; real-run evidence pending |
| R15 [architecture views] Stage table identifies agent, artifact, check | architecture/views/stage-map.md | INITIAL DESIGN CHECKED; runtime evidence pending |
| R16 [Part 1] Fork software repository and pin exact commit; tests under five minutes | REPOSITORY_PLAN.md; evidence/baseline/ | COVERED IN PLAN; execution/submission evidence pending |
| R17 [Part 1] Five real-user issues: 2 bugs, 2 small features, 1 vague | experiment/issues/; results/runs.md | COVERED IN PLAN; execution/submission evidence pending |
| R18 [Part 1] 2–4 hidden acceptance tests per issue, outside repository | private evaluator outside repository; hash manifest only public | COVERED IN PLAN; execution/submission evidence pending |
| R19 [Part 1 + Rules] Repository secrets for API keys; none in code, prompts, logs; fork-event secret limitations | settings evidence; sanitized scan | COVERED IN PLAN; execution/submission evidence pending |
| R20 [Part 1] Protect main against direct pushes, including bypass settings | repository rules evidence | COVERED IN PLAN; execution/submission evidence pending |
| R21 [Part 2] Commit component view and first ADRs BEFORE writing agent code | repository git history | READY FOR DESIGN-ONLY COMMIT; inspect resulting ancestry |
| R22 [Part 2] Keep invalidated ADR, mark Superseded, add replacement explaining evidence | architecture/decisions/ | COVERED IN PLAN; execution/submission evidence pending |
| R23 [Part 3] Implement workflow and agent code; least job permissions; issues/comments untrusted; followable artifacts/PR/review | workflow/; .github/workflows/; results/runs.md | COVERED IN PLAN; execution/submission evidence pending |
| R24 [report] report.pdf at most 8 pages plus appendices | report.pdf | COVERED IN PLAN; execution/submission evidence pending |
| R25 [What to Submit] Architecture: three views and stage assignment (suggested 2 pages) | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R26 [What to Submit] Design decisions: summary table of decision/chosen/rejected/reason/status; discuss 3 most important; full ADRs separate (2.5 pages) | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R27 [What to Submit] Decision experiments: test TWO ADRs, side-by-side results, resulting design changes (1.5 pages) | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R28 [What to Submit] Results: stage pass rates, hidden tests, reviewer successes/errors, MERGE_READINESS_CHECK (1 page) | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R29 [What to Submit] Hindsight: first decision to change and why (half a page) | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R30 [What to Submit] Limitations/threats to validity: at least THREE | report.pdf; results/ | COVERED IN PLAN; execution/submission evidence pending |
| R31 [demo] Real demo video at most 5 minutes showing full issue-to-posted-review run; demo.mp4 or README link | demo.mp4 or README.md | COVERED IN PLAN; execution/submission evidence pending |
| R32 [submission] 2025811002_a3_AutoSE.txt contains ONLY GitHub repository link | 2025811002_a3_AutoSE.txt | COVERED IN PLAN; execution/submission evidence pending |
| R33 [repo tree] README: fork URL, pinned commit, models, how to trigger; report.pdf; demo; architecture/views and decisions; workflow copy + code + prompts; experiment/issues, hidden_tests, seeded_prs, variants.md; results/results.csv and runs.md | repository tree | COVERED IN PLAN; execution/submission evidence pending |
| R34 [repo tree] FIVE reviewer-check PRs with saved diffs and labels | experiment/seeded_prs/; results/runs.md | COVERED IN PLAN; execution/submission evidence pending |
| R35 [repo visibility] Public until grades released OR TAs added so every link is accessible | repository settings | COVERED IN PLAN; execution/submission evidence pending |
| R36 [Rules] Mutations only in student/team-owned fork, never upstream | repository allowlist and remote evidence | COVERED IN PLAN; execution/submission evidence pending |
| R37 [Rules] Hard provider spending limit BEFORE first run; report total tokens | provider evidence; usage ledger | COVERED IN PLAN; execution/submission evidence pending |
| R38 [Rules] README acknowledges substantial AI help; student reviews generated work; ADRs and reasoning student-owned | README disclosure; student review record | INITIAL DESIGN CHECKED; runtime evidence pending |
| R39 [Rules] All runs, PRs and results real/linkable; fabricated run earns zero | results/runs.md; raw logs | COVERED IN PLAN; execution/submission evidence pending |
| R40 [grading emphasis] Architecture reasoning is primary; no numeric mark weights supplied; negative results count equally | report; worksheet | COVERED IN PLAN; execution/submission evidence pending |

## Unresolved requirements

Provider/model/effort, API compatibility, hard provider cap, secret and separate explicit paid approval remain pending under ADR-006. Enable Issues and establish protected main with actual no-direct-push rules; current tools cannot administer settings. Hosted pipeline, exact-commit CI, posted independent reviews, five issues/seeded PRs, hidden tests and two experiments remain future work. A real-run sequence, report <=8 pages, demo <=5 minutes, link/technical audit and final submission file require actual execution evidence; local fixtures cannot establish completion.

Initial design-first ordering is established only after the ensuing Git commit succeeds and its parent/files are inspected. Record exact SHA externally. No date/SHA is invented. This initial audit preserves open requirements rather than claiming all assignment work is complete.
