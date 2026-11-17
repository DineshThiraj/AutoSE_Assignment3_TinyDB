# Implementation contract — reviewed architecture elaboration

This is Codex-authored operational detail implementing the student's D1–D10 choices. It does not replace their rationale. Status: design baseline, no implementation or hosted evidence claimed.

## Fixed stages and isolation

A trusted Python controller validates schemas, budgets, immutable hashes and stage transitions. GitHub Actions uses a statically bounded job graph: admission; requirements/design; at most two implementation/build/testing attempts; release/CI; independent review; at most one routed repair cycle and second review; final evidence. The second cycle starts at the requested stage, preserves earlier validated artifacts and invalidates all downstream evidence. Requirements and design are separate model calls; implementation and test authoring share a role but use distinct stage requests. No free-form planner or cross-workflow recursion.

Broker jobs read files as inert bounded UTF-8; they never import TinyDB, generated tests, repository plugins or generated scripts. Their only secret is the provider key. No shell tool is exposed to a model. Code changes are structured file replacements for regular tinydb/*.py files; tests are new tests/test_autose_*.py files, never baseline-test edits. Trusted code materializes validated edits and derives diff.patch. Deny absolute/traversal/backslash/symlink/special-file paths, workflow/controller/reuse edits, oversized files and source deletions. Original tracked tests/config stay byte-identical.

Execution jobs have no provider key or repository write permission, persist-credentials=false and no Actions runtime credentials inside target execution. Hosted target execution uses a disposable container with network disabled, read-only source/root, bounded CPU/memory/PIDs, no capabilities and only an output directory writable. Build the trusted pytest image before mounting target source. The publisher runs trusted code only and never installs/imports the target. Local fixture integration uses actual pinned TinyDB and pytest with a minimal environment; fixture runs are explicitly not security isolation evidence or hosted execution.

Reviewer broker receives its own trusted prompt plus frozen issue, exact released diff and sanitized latest TinyDB source/tests snapshot. Exclude spec/design, logs, conversations, hidden tests, seed labels, Git metadata and run state. Reviewer can request a fixed full-suite execution through a separate no-secret executor; it cannot edit or push. The trusted publisher, not the model, posts the verdict for the exact reviewed commit. A posted COMMENT carrying an APPROVE model verdict must not be misreported as a GitHub APPROVED review if the GitHub identity cannot approve.

## Admission, recovery and budgets

Exact fork allowlist: DineshThiraj/AutoSE_Assignment3_TinyDB. Authorized issue events only: autose label or exact /autose comment, non-bot actor, current write/maintain/admin permission from GitHub. PR comments and lookalike strings are rejected. Freeze current issue content and hash at admission. Source of implementation is the pinned TinyDB commit; trusted orchestration is loaded from an explicitly frozen reviewed base SHA. A1 exact-scope readiness is checked separately from trigger permission: admission does not invent approval for inferred requirements. Explicit issue scope plus authorized trigger can establish authorization of that scope; proposals/critical unknowns must stop needs_clarification.

Per-issue concurrency (cancel-in-progress=false), deterministic issue branch and PR reconciliation provide the durable run-to-PR index. Every event/run/attempt has distinct immutable artifacts; replayed completed events are not new runs. Interrupted publication reconciles branch head, tree and PR before continuing. Do not claim exactly-once external API operations. Artifacts retain 90 days where supported; essential evidence is exported into owned results storage for grading.

Operational starting ceilings (assistant refinement, adjustable only within recorded paid authorization): two total review rounds, two build/test attempts per round, 24 total model requests, 40-minute reasoning/execution budget, five-minute test process, 15-minute model request deadline. A global token ceiling is mandatory configuration after provider pricing review. Global budgets take precedence over loops. HTTP retries never silently create extra model calls. Timeouts can still incur charges. Missing usage is unknown and blocks spending-sensitive continuation, never zero.

## Gates and artifacts

Use views/stage-map.md as the six-stage contract. Stage 1 preserves requirements_spec.md, assumptions_questions.md, validation_summary.md and spec.md alias; structured ACs include source/requirement IDs, precondition, action, expected result, measurement and pass/fail. Preserve A1 evidence classes/approval statuses; critical unknowns stop. Targeted fresh semantic validation checks testability and unsupported scope. Stage 2 grounds every AC in actual source files/functions and addresses all five A2 constraints.

Stage 3 produces a real diff, validates policy and runs fixed compile. Stage 4 authors an added asserted test per AC, restores immutable original tests, runs the full original/new suite and checks JUnit collection/passes against baseline identifiers. AST/assert mapping is a structural check, not semantic proof; runtime Python can monkeypatch behavior and no automatic test gate establishes absence of malicious semantics.

Stage 5 publishes only the tested source tree on an allowlisted non-main branch; saves commit/tree/patch hashes and pr.md; verifies open PR target/base/head and actual required CI from the known workflow at that exact head. Missing, pending, skipped, stale or failing CI cannot pass. GITHUB_TOKEN-triggered CI may require explicit human approval; preserve pending status rather than changing credential type silently. No separately privileged App/PAT is selected by this architecture.

Stage 6 posts review.md and a real GitHub review link pinned to the current head. Findings include file/line/evidence and validated routing to requirements/design/implementation/testing. After two total review rounds the workflow terminates even if unapproved; exhausted is not approved or merge-ready.

MERGE_READINESS_CHECK records six gates, base/head/tree identity, original/new tests, exact-head CI, reviewer verdict/unresolved findings, rounds, hidden tests (unknown until separate evaluation), source policy and human decision=pending. It never invokes merge or auto-merge APIs.

## Git history and hosted setup

Initial design-only commit is a direct child of edff96aeb2616402e9489d46e90a592c05565621. Implementation commits are descendants; no backdating/reset/force push. Preserve master and historical branches. The assignment requires protected main: create main using ordinary refs, set default through an authorized administrative route, enable Issues, configure PR-only protection including no direct-push bypass, then publish workflow changes under human control. Detailed protection/settings access is currently unavailable through the connector. No protection or hosted execution is claimed.

## Deferred provider and experiments

ADR-006 intentionally leaves provider/model/effort unresolved. Implement a provider-neutral request/response contract and deterministic local fixtures without sending paid calls. A hosted adapter must record exact provider endpoint, SDK/protocol, model, effort, supported usage fields and frozen config. Preflight must verify API support, named repository secret, provider-enforced hard cap and separate explicit paid authorization before enabling live calls. A local config assertion is not provider enforcement evidence.

After one real nonexperimental vertical slice works, freeze two decision experiments (candidate D3 handoff and D8 reviewer prompt) with fixed source/model/tool/budget/task/test controls. Keep private hidden tests and five seeded ground truths outside Git history and all agent inputs until experiments finish. Preserve valid failures and null unavailable metrics. The real-run sequence/report/video/submission remain later deliverables; do not manufacture them from fixture traces.
