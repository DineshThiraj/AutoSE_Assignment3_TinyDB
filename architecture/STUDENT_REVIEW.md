# Student architecture review — received 2026-11-17

Source: the user's D1–D10 response in this conversation, received after the approval worksheet. Codex transcribed and formatted it. The user labelled explanations “suggested reason”; that label is preserved below. This record establishes the supplied choices and review, not an independent claim that all text originated without AI assistance. Assistant proposals remain distinguishable in architecture/DECISION_WORKSHEET.md. No spending authorization was supplied.

Nine substantive choices accepted: D1–D5 and D7–D10. D6 explicitly defers provider/model/effort and does not count toward the minimum eight accepted architecture choices. All ten supplied records contain choice, suggested reason, rejection/reason and accepted drawback. Nygard formatting and implementation elaboration are Codex assistance.

## D1: Splitting the work

Status: Accepted.

- **choice:** Four reasoning roles for requirements, design, implementation/testing and independent review, with deterministic testing and release control
- **suggested reason:** This separates responsibilities without the overhead of six separate reasoning agents, and allows the A1 and A2 artifacts to be reused
- **rejected:** One agent handling everything
- **why rejected:** It mixes implementation, verification and review context, making independent review less credible
- **accepted drawback:** More hand-offs and model-context overhead.

## D2: Control flow

Status: Accepted.

- **choice:** Deterministic state machine with explicit stage gates and two total review rounds
- **suggested reason:** The six required stages and retry boundaries should be enforced by code rather than model discretion
- **rejected:** Unrestricted model planner
- **why rejected:** It could skip checks or repeatedly retry without respecting the budget
- **accepted drawback:** More controller code and less flexibility.

## D3: Handoffs

Status: Accepted.

- **choice:** Full validated specification and design artifacts for implementation, and a separate restricted reviewer context
- **suggested reason:** This preserves acceptance criteria and architecture constraints across hand-offs
- **rejected:** Passing complete conversations to every agent
- **why rejected:** It wastes context and could bias the reviewer
- **accepted drawback:** Higher token usage.

Additional user instruction, verbatim:

> For vague issues, the A1 readiness gate must verify that acceptance criteria are testable. If critical requirements remain ambiguous, save the draft spec and clarification questions, stop with needs_clarification, and resume only after an authorized clarification. Do not invent requirements.

## D4: State

Status: Accepted.

- **choice:** Immutable execution artifacts, unique attempt identifiers, hashes and a durable run-to-PR index
- **suggested reason:** Failures and interrupted runs should remain traceable, while restarts must check existing branches and PRs to prevent duplicates
- **rejected:** Using Actions cache as the authoritative state
- **why rejected:** Cache availability and retention are unsuitable for recovery and grading evidence
- **accepted drawback:** Additional storage and reconciliation logic.

## D5: Tools

Status: Accepted.

- **choice:** Restricted model-broker tools with isolated patch application, test execution and a separate GitHub publisher
- **suggested reason:** Untrusted generated code and tests must not execute with provider credentials or repository write authority
- **rejected:** One general shell agent holding all credentials
- **why rejected:** It creates unnecessary exposure to malicious code or prompt injection
- **accepted drawback:** Additional validation, isolation and artifact transfers.

## D6: Models

Status: Deferred.

- **choice:** Defer exact hosted provider, model and reasoning effort
- **suggested reason:** Local Codex authentication does not establish API availability or cost controls within GitHub Actions. Select a supported model after verifying provider access and a hard spending cap
- **rejected:** Choosing an unverified model or silently changing models across experiments
- **why rejected:** This risks failed hosted execution and confounded comparisons
- **accepted drawback:** Hosted model-driven runs remain blocked until the model configuration is approved.

## D7: Stage checks

Status: Accepted.

- **choice:** Deterministic structural checks, real build and test execution, exact-commit CI, plus targeted semantic checks
- **suggested reason:** Tests and recorded CI status provide stronger evidence than agent-generated success statements
- **rejected:** Trusting an agent's claim that its stage passed
- **why rejected:** It does not prove which commands ran or which commit was tested
- **accepted drawback:** Additional verification time and imperfect defect coverage.

## D8: Reviewer independence

Status: Accepted.

- **choice:** Fresh independent reviewer context, separate prompt, sanitized latest PR source and diff, with no push tools
- **suggested reason:** The reviewer must evaluate the actual change without relying on implementation reasoning, and seeded cases can measure its mistakes
- **rejected:** The implementer reviewing its own work in the same conversation
- **why rejected:** Its previous assumptions can influence the outcome
- **accepted drawback:** Additional cost, latency and possible false positives or missed defects.

## D9: Safety and failures

Status: Accepted.

- **choice:** Provider spending cap, enforced timeouts, retry budgets, model-call limits and fail-closed errors
- **suggested reason:** Trusted code must enforce safety limits because prompt instructions alone cannot guarantee them
- **rejected:** Unlimited retries with prompt-only safety instructions
- **why rejected:** This permits uncontrolled execution or spending
- **accepted drawback:** Some legitimate difficult tasks may stop unfinished.

## D10: Triggers

Status: Accepted.

- **choice:** Authorized maintainer-applied autose label or exact /autose issue comment, with permission checks and duplicate-event handling
- **suggested reason:** This provides a convenient GitHub trigger without allowing arbitrary issue authors to initiate costly work
- **rejected:** Allowing every issue author to trigger the workflow
- **why rejected:** Issue authorship does not establish current repository write permissions
- **accepted drawback:** Additional authorization, concurrency and idempotency logic.

## Review gate and unresolved operational setup

At least eight complete substantive decisions: PASS (nine). Two total review rounds and stop-on-critical-ambiguity are explicit. Exact provider/model/effort, API support, repository secret, provider-enforced hard cap and separate paid-call approval remain pending. No hosted model-driven run may begin until those are resolved.

Initial architecture may now be committed, followed by safe local provider-independent implementation and tests. Hosted configuration must be added transparently after verification; a deferred model choice is not a hidden default.
