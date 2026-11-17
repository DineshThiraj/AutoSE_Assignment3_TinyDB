# Verified requirements matrix

Source: ASSIGNMENT_3.md, byte-identical to the connected GitHub raw source on 2026-11-16; SHA-256 `a0452d595904acaa249ea3fe4308c0288450d1f1b66d36e74ed39cc5182cccb9`. See evidence/source/verification.json. Source labels below locate the authentic section. Evidence paths describe planned destinations unless status explicitly says verified. Risk labels are engineering estimates, not published mark allocations.

| Requirement | Evidence location | Verification method | Status | Risk of losing marks |
| --- | --- | --- | --- | --- |
| R01 [front matter] Deadline 2026-11-21 23:59 IST (18:29 UTC); extension only if requested before deadline, 3 days total across assignments | evidence/source/verification.json | Compare source front matter; no extension assumed | VERIFIED | Critical |
| R02 [Mission] Hosted Actions workflow in .github/workflows triggered by maintainer label or comment | repository/.github/workflows/autose.yml; results/runs.md | Actual issue event and Actions URL | IMPLEMENTED LOCALLY; HOSTED OPEN | Major |
| R03 [six-stage table] Requirements: Reuse actual A1 skill; artifact spec.md; gate: All criteria testable | results/<run>/spec.md | Inspect artifact AND objective gate evidence | LOCAL FIXTURE VERIFIED; HOSTED OPEN | Major |
| R04 [six-stage table] Design: Use actual A2 ARCHITECTURE.md; artifact design.md; gate: Names actual files and functions | results/<run>/design.md | Inspect artifact AND objective gate evidence | LOCAL FIXTURE VERIFIED; HOSTED OPEN | Major |
| R05 [six-stage table] Implementation: New branch following design; artifact diff.patch; gate: Code builds | results/<run>/diff.patch | Inspect artifact AND objective gate evidence | LOCAL FIXTURE VERIFIED; HOSTED OPEN | Major |
| R06 [six-stage table] Testing: Write a test per criterion; failing tests return to implementation; artifact test_report.md; gate: New and all existing tests pass | results/<run>/test_report.md | Inspect artifact AND objective gate evidence | ACTUAL TINYDB FIXTURE VERIFIED; HOSTED OPEN | Major |
| R07 [six-stage table] Release: Push branch; save real PR link; artifact pr.md; gate: Open PR and CI passes | results/<run>/pr.md | Inspect artifact AND objective gate evidence | API CONTRACT TESTED; HOSTED OPEN | Major |
| R08 [six-stage table] Review: Separate reviewer; route fixes to relevant earlier stage, bounded at two; artifact review.md; gate: Approval or two review rounds exhausted | results/<run>/review.md | Inspect artifact AND objective gate evidence | ROUTING/BOUNDS TESTED; REAL REVIEW OPEN | Major |
| R09 [stage failure] Unpassed gate explains failure in its artifact and stops; bounded earlier-stage returns | results/<run>/events.jsonl; stage artifacts | Inject model/build/test failures and inspect transitions | LOCAL FAILURE GATES TESTED; HOSTED OPEN | Major |
| R10 [independence] Reviewer sees only issue, diff, latest PR checkout; separate prompt; read/run permission, no push; no implementer reasoning | review prompt; permission policy; review input manifest | Inspect mounts, job token and provided inputs; adversarial check | CONTEXT/PERMISSIONS TESTED; CONTAINERS UNVERIFIED | Critical |
| R11 [architecture] Human alone decides final merge; workflow never merges | workflow permissions; PR status | Inspect code and hosted terminal state | NO MERGE CODE; HOSTED TERMINAL STATE OPEN | Critical |
| R12 [Decisions] At least 8 ADRs from D1–D10 in Nygard format; concrete alternatives and consequences | architecture/decisions/ | Count decision coverage and format; student-authored reasoning | 9 ACCEPTED + D6 DEFERRED; TEN ADRS COMMITTED | Critical |
| D1 [Decisions table] agent splitting | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D2 [Decisions table] control flow and routing | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D3 [Decisions table] handoffs and omitted context | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D4 [Decisions table] state and restart | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D5 [Decisions table] tools and least privilege | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D6 [Decisions table] models: ability, cost, speed, diversity | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | DEFERRED BY STUDENT | Major |
| D7 [Decisions table] checks and final gate authority | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D8 [Decisions table] reviewer independence and agreement bias | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D9 [Decisions table] safety, budgets, stuck stages, injection | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| D10 [Decisions table] triggers, authorization, concurrency | architecture/DECISION_WORKSHEET.md; future ADR | Student reasoning then inspect implementation | STUDENT CHOICE RECORDED; ADR COMMITTED | Major |
| R13 [architecture views] Component view: agents, tools and calls | architecture/views/component.dot; component.svg | Render and compare with implemented boundaries | REVIEWED INITIAL DESIGN COMMITTED | Major |
| R14 [architecture views] Sequence view of one REAL run trigger through review | architecture/views/sequence-real-run.* | Render and cross-check against hosted events | OPEN | Major |
| R15 [architecture views] Stage table identifies agent, artifact, check | architecture/views/stage-map.md | All six rows agree with implementation | REVIEWED SIX-STAGE CONTRACT COMMITTED | Major |
| R16 [Part 1] Fork software repository and pin exact commit; tests under five minutes | REPOSITORY_PLAN.md; evidence/baseline/ | Verify ownership, fork parent, commit tree, timed tests | FORK/PIN/LOCAL BASELINE VERIFIED; HOSTED OPEN | Critical |
| R17 [Part 1] Five real-user issues: 2 bugs, 2 small features, 1 vague | experiment/issues/; results/runs.md | Count and classify actual hosted issues | FIVE LOCAL DRAFTS; HOSTED OPEN | Major |
| R18 [Part 1] 2–4 hidden acceptance tests per issue, outside repository | private evaluator outside repository; hash manifest only public | Count 10–20 tests total; inspect isolation and freeze | OPEN | Critical |
| R19 [Part 1 + Rules] Repository secrets for API keys; none in code, prompts, logs; fork-event secret limitations | settings evidence; sanitized scan | Inspect secret names only and scan tracked/public artifacts | OPEN | Critical |
| R20 [Part 1] Protect main against direct pushes, including bypass settings | repository rules evidence | Inspect actual rules and required PRs/checks | OPEN | Critical |
| R21 [Part 2] Commit component view and first ADRs BEFORE writing agent code | repository git history | Inspect parent commits and authored files; do not backdate | VERIFIED: DESIGN COMMIT PRECEDES AGENT CODE | Critical |
| R22 [Part 2] Keep invalidated ADR, mark Superseded, add replacement explaining evidence | architecture/decisions/ | Compare run observations and immutable old decision | CONDITIONAL | Major |
| R23 [Part 3] Implement workflow and agent code; least job permissions; issues/comments untrusted; followable artifacts/PR/review | workflow/; .github/workflows/; results/runs.md | Source audit and hosted execution | LOCAL SOURCE + 66 CHECKS PASSED; HOSTED OPEN | Major |
| R24 [report] report.pdf at most 8 pages plus appendices | report.pdf | pdfinfo and rendered page inspection | OPEN | Major |
| R25 [What to Submit] Architecture: three views and stage assignment (suggested 2 pages) | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R26 [What to Submit] Design decisions: summary table of decision/chosen/rejected/reason/status; discuss 3 most important; full ADRs separate (2.5 pages) | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R27 [What to Submit] Decision experiments: test TWO ADRs, side-by-side results, resulting design changes (1.5 pages) | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R28 [What to Submit] Results: stage pass rates, hidden tests, reviewer successes/errors, MERGE_READINESS_CHECK (1 page) | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R29 [What to Submit] Hindsight: first decision to change and why (half a page) | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R30 [What to Submit] Limitations/threats to validity: at least THREE | report.pdf; results/ | Check required content against real evidence | OPEN | Major |
| R31 [demo] Real demo video at most 5 minutes showing full issue-to-posted-review run; demo.mp4 or README link | demo.mp4 or README.md | Play video, verify duration and actual URLs | OPEN | Major |
| R32 [submission] 2025811002_a3_AutoSE.txt contains ONLY GitHub repository link | 2025811002_a3_AutoSE.txt | Exact filename and one URL, no placeholder | OPEN | Critical |
| R33 [repo tree] README: fork URL, pinned commit, models, how to trigger; report.pdf; demo; architecture/views and decisions; workflow copy + code + prompts; experiment/issues, hidden_tests, seeded_prs, variants.md; results/results.csv and runs.md | repository tree | Compare inventory and workflow mirror hashes | PARTIAL TREE; REPORT/DEMO/REAL EVIDENCE OPEN | Major |
| R34 [repo tree] FIVE reviewer-check PRs with saved diffs and labels | experiment/seeded_prs/; results/runs.md | Ground truth frozen privately; inspect 5 real PR/review links | OPEN | Major |
| R35 [repo visibility] Public until grades released OR TAs added so every link is accessible | repository settings | Open links with examiner-equivalent access | CURRENT PUBLIC VISIBILITY VERIFIED | Major |
| R36 [Rules] Mutations only in student/team-owned fork, never upstream | repository allowlist and remote evidence | Fail closed on owner/repo mismatch | OPEN | Critical |
| R37 [Rules] Hard provider spending limit BEFORE first run; report total tokens | provider evidence; usage ledger | Verify enforced provider cap (soft alert insufficient), sum actual usage | OPEN | Critical |
| R38 [Rules] README acknowledges substantial AI help; student reviews generated work; ADRs and reasoning student-owned | README disclosure; student review record | Check provenance, no invented approvals | DISCLOSURE + STUDENT RECORD PRESENT; IMPLEMENTATION REVIEW PENDING | Critical |
| R39 [Rules] All runs, PRs and results real/linkable; fabricated run earns zero | results/runs.md; raw logs | Resolve URLs and compare SHAs, times, outcomes | OPEN | Critical |
| R40 [grading emphasis] Architecture reasoning is primary; no numeric mark weights supplied; negative results count equally | report; worksheet | Evidence-supported claims, preserve unsuccessful attempts | TRACKED | Major |

## Counts, ambiguity, and easy omissions

Six fixed ordered stages, six named artifacts (release also requires PR link); at least eight of ten decision topics; three architecture views (one is a table); five issues (2 bug + 2 feature + 1 vague); 2–4 private tests each (10–20 total); two ADR experiments; five seeded reviewer-check PRs; at most two review rounds; at most eight main report pages; at least three limitations; at most five demo minutes; source tests under five minutes. No explicit minimum experiment replicate count, total Actions-run count, or required model is given. Do not import A2's 12-trial design as an A3 mandate.

The listed report section allocations sum to 8.5 pages before limitations. Treat the explicit eight-page ceiling as binding and compress sections while retaining all content; seek course clarification if strict allocations are enforced. MERGE_READINESS_CHECK is named but not defined: propose an evidence-backed checklist, do not pretend a supplied schema exists. Reviewer-check PRs appear only in the required tree; retain this easily missed count. Their precise defect mixture is unspecified.

The instruction to keep tests outside the repository conflicts with the tree's experiment/hidden_tests directory. Proposed resolution: keep only a README and cryptographic commitments there during experiments, with evaluator code outside all agent checkouts and Git history. Do not publish hidden code before all trials finish. Document this interpretation; do not silently expose tests. Student/course confirmation remains useful.

Engaging/insightful video earns unspecified brownie points; SDK/framework and model diversity are optional. The SVG in the assignment is illustrative, not a mandated architecture. No other extra-credit rubric or numeric mark scheme is published in this source.

## Additional user requirements (not asserted as course mandates)

| Requirement | Evidence location | Verification method | Status | Risk of losing marks |
| --- | --- | --- | --- | --- |
| U01 Verify and reuse prior materials without modifying A1/A2; source paths and hashes | REUSE_RECORD.md; reproducibility-manifest.json | Compare before/after digests | IN PROGRESS | Provenance risk |
| U02 Student review before final ADRs; explicit external authorization and spending approval | preparation/STUDENT_REVIEW.md; AUTHORIZATION_REQUEST.md | Retain actual user response | PENDING | Critical boundary |
| U03 Authorization/model/test/reviewer/budget failure cases; timeouts, deduplication, no privileged untrusted execution | SECURITY_PLAN.md; future controller tests | Adversarial failure tests | PLANNED | Engineering risk |
| U04 Freeze controls; fresh reviewer; no rerunning valid failures; complete logs, machine results and unavailable metrics explicit | experiment/variants.md; results/ | Protocol audit | DRAFT | Validity risk |
| U05 Render report/diagrams; final hosted audit; reproducible demo or honest recording guide | FINAL_AUDIT.md; report; demo guide | Inspect artifacts and real links | OPEN | Completion risk |
| U06 Durable progress; exact final handoff; no claim of completion with missing evidence | PROGRESS.md; FINAL_AUDIT.md | Resume checklist | ACTIVE | Completion risk |

## Continuation evidence — 2026-11-17

Nine accepted student records and D6 deferral are in preparation/STUDENT_REVIEW.md. Design-only commit 67c9b3c4286f598d5d415fb60433870cf63035a8 directly descends from the original pin. Local implementation has 66 passing controller/security/API-contract/workflow checks. Actual TinyDB fixture: ineffective change yields four failures with 228 original passes; bounded repair yields 232 passes. All model/GitHub/CI/review transports in these tests are fixtures; hosted evidence remains zero. See repository/results/local-validation/summary.json and evidence/design-commit.json. Docker daemon access is denied; actionlint unavailable. Repository setup/provider/cap/secret/paid approval and all execution/submission deliverables remain open.
