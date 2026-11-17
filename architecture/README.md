# Initial reviewed architecture

Student review received 2026-11-17: nine accepted substantive decisions and one deferred model decision. See decisions/ADR-001.md through ADR-010.md, STUDENT_REVIEW.md and student-decisions.json. Codex formatted the student's supplied choices; reasons retain their “suggested reason” provenance.

The component view and stage map describe the chosen design, not implemented behavior. sequence-plan.txt and sequence-plan.svg are explicitly proposed. The assignment's real-run sequence view remains an execution deliverable and will be derived from a real hosted Actions run, PR and posted review.

Design source baseline: edff96aeb2616402e9489d46e90a592c05565621, tree 52a3d82ceab13b0da98cc3b2808218ac02fde924. The initial architecture commit must be a direct child of that baseline and contain no new agent implementation. Its exact SHA is recorded outside the commit in evidence/design-commit.json after creation.

Safe local development can use deterministic test fixtures clearly marked as fixtures. Such runs do not establish model capability, hosted execution or GitHub review success. Provider/model/effort, enforced hard cap, secrets and separate paid authorization remain unresolved under ADR-006.
