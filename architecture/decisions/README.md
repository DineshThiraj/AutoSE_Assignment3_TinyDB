# Architecture decision summary

The original ten Nygard ADRs and their history are preserved. The student supplied nine accepted decisions and explicitly deferred D6. ADR-011 and ADR-012 are retrospective implementation refinements assembled from measured local evidence. The student must review their final wording and reasoning.

| ADR | Decision and selected option | Rejected alternative | Main rationale | Status |
| --- | --- | --- | --- | --- |
| [001](ADR-001.md) · D1 | Four reasoning roles, deterministic test/release control | One agent for all stages | Preserve specialization and independent review without six reasoning agents | Accepted |
| [002](ADR-002.md) · D2 | Fixed state machine, gated transitions and two review rounds | Unrestricted planner | Enforce retry and transition budgets in code | Accepted |
| [003](ADR-003.md) · D3 | Validated spec/design and separate reviewer envelope | Whole conversations as context | Preserve exact scope and avoid reviewer anchoring | Accepted |
| [004](ADR-004.md) · D4 | Hashed immutable artifacts, attempt IDs and run-to-PR reconciliation | Actions cache as authority | Traceable failure and duplicate prevention | Accepted |
| [005](ADR-005.md) · D5 | Restricted broker, isolated execution, separate publisher | One credentialed shell agent | Keep candidate code away from model and write credentials | Accepted |
| [006](ADR-006.md) · D6 | Defer exact hosted model/provider/effort | Unverified selection or switching models mid-experiment | Require account entitlement and spending controls | Deferred |
| [007](ADR-007.md) · D7 | Deterministic plus semantic checks, actual execution and exact commit | Agent-reported success | Validate what ran before transferring authority | Accepted; operational refinement in ADR-011 |
| [008](ADR-008.md) · D8 | Fresh restricted reviewer context and no push rights | Implementer self-review | Reduce anchoring and prevent reviewer edits | Accepted |
| [009](ADR-009.md) · D9 | Explicit time/call/token/USD limits and fail-closed handling | Prompt-only restraint and unlimited retries | Make safety limits enforceable | Accepted; operational refinement in ADR-012 |
| [010](ADR-010.md) · D10 | Maintainer issue action with auth and deduplication | Every author can trigger | Issue authorship does not confer authority | Accepted; current trial is comment-only |
| [011](ADR-011.md) · D7 | Trusted verifier outside the candidate process | Candidate JUnit as authoritative | A local false-success case crossed the old gate | Retrospective; student review pending |
| [012](ADR-012.md) · D9 | Atomic, request-bound consumption per provider call | Read-only reusable grant | Three concurrent callers reached a provider double on one grant | Retrospective; student review pending |
