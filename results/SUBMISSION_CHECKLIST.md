# Final submission checklist · 2025811002

| Criterion | Status | Evidence or next action |
| --- | --- | --- |
| Correct GitHub fork and historical source pin | PASS | Public TinyDB fork, pin `edff96aeb2616402e9489d46e90a592c05565621`. |
| Design revision precedes implementation | PASS | Design `67c9b3c`, implementation `ba6fdaf`, linear ancestry verified. |
| At least eight Nygard decisions and summary | PASS | Ten original ADRs and two retrospective refinements. Nine student-accepted decisions, D6 deferred. |
| Final reasoning and AI-produced materials reviewed by student | NEEDS HUMAN ACTION | Original choices are preserved. Read the report, retrospective ADRs and code disclosure before publication. |
| Component view, sequence view, stage map | PASS | Current component and stage views, observed partial sequence, proposed continuation clearly labeled. |
| Six staged artifacts, gates and reviewer separation | PASS | Source and local fixture demonstrate the contracts. Human merge authority is explicit. |
| Complete real GitHub issue-to-posted-review trace | MISSING | The only listed issue-triggered run skipped all 39 downstream jobs. |
| Two measured architectural comparisons | PASS | D7 verdict ownership and D9 per-call consumption. Local controls only, with validity limits. |
| Five issues (2 bugs, 2 features, 1 vague) | PASS | Public #3–#7 and original authored drafts. |
| 2–4 frozen private tests per issue | PASS | Counts 4/4/4/4/3. Redacted metadata only. |
| Private outcomes on hosted agent fixes | MISSING | Hosted candidates were not evaluated. Published aggregates are controls. |
| Reviewer-check input examples | PASS | Five local seeded diffs and labels, verified to apply. |
| Five hosted seeded PR reviews and reviewer accuracy | MISSING | No seeded PRs or scored reviews executed. |
| Public results, denominators and readiness evidence | PASS | `results.csv`, `runs.md` and genuine read-only GitHub links. Fixture readiness is false. |
| Production billing hard cap, API secret and token reporting | MISSING | Hosted project entitlements, secret and cap unverified, coordinator total not measured. No paid hosted calls observed. |
| PDF at most eight pages | PASS | Eight A4 pages. The editable source is `report.html`. |
| Demo at most five minutes | PASS | MP4 is 4:36. Actual public evidence and local records, synthesized narration. Script provided. |
| Demo of complete hosted run | MISSING | The provided walkthrough is a partial demonstration. |
| README with workflow, constraints, reproducibility and disclosure | PASS | Includes report, demo, evidence, and human decision instructions. |
| Production configurations, original pin and old evidence preserved | PASS | Both enablement flags remain false, original tests unchanged, Docker and private manifest checksums matched. |
| Publish and verify default-branch discoverability | NEEDS HUMAN ACTION | Review the explicit submission path list. Submit by a documentation-only PR through the normal protected-main process. Keep draft PR #8 separate. |
| Course TXT | PASS | `2025811002_a3_AutoSE.txt` in the workspace root. Only the fork URL and newline. |
| Course portal upload | NEEDS HUMAN ACTION | Upload that TXT under Assignment 3 and confirm submission receipt. |

## Rebuild the report

From the repository root with Chrome available:

```sh
pdf_profile=$(mktemp -d)
google-chrome --headless --disable-gpu --user-data-dir="$pdf_profile" \
  --no-pdf-header-footer --print-to-pdf="$PWD/report.pdf" "file://$PWD/report.html"
pdfinfo report.pdf
```

## Submission boundary

The compiled PDF, editable source, video, recording script, evidence summaries, architecture refinements and local seeds are available in the worktree. The previously uncommitted security patch remains separate. A default-branch submission PR should carry the submission files only. The README links to the recorded code on the draft branch. Follow the repository’s existing protections and leave both production flags disabled.
