# Run and review evidence

Read-only GitHub inventory on 20 November 2026 verified the public fork, protected `main`, issues #3–#7, eight listed Actions runs and three infrastructure PRs. Among the listed runs, one was triggered by an issue comment. The PR #8 reviews endpoint returned an empty list.

| Record | Evidence | Scope |
| --- | --- | --- |
| [44069611603](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44069611603) | Issue-comment job conclusions: admission and finalization succeeded as jobs, 39 downstream jobs skipped. | No hosted SDLC stage passed or attempted in this trace. |
| [44068724918](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44068724918) | Earlier hosted baseline CI success for [PR #2](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/pull/2). | 228 baseline tests in the prior evidence record. |
| [44280528872](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/actions/runs/44280528872) | `tinydb-tests` success on head `f6c727d` for [draft PR #8](https://github.com/DineshThiraj/AutoSE_Assignment3_TinyDB/pull/8). | Earlier base verifier. No protected-dispatch or new-authority deployment evidence. |
| [PR #8 / reviews endpoint](https://api.github.com/repos/DineshThiraj/AutoSE_Assignment3_TinyDB/pulls/8/reviews) | Empty review list. PR open and draft. | No posted reviewer-agent URL available. |
| [Local flow fixture](local-validation/summary.json) | Real compile and pytest. First attempt 228/232, bounded repair 232/232. | Model and GitHub transports used test doubles. |
| [Recorded local Docker snapshot](docker-observed.json) | Three outcomes matched expectations. Five observed containers. Positive 228 baseline + 4 generated. | Host execution only. |
| [Private acceptance metadata](../experiment/hidden_tests/README.md) | 19 frozen cases and 23 archived controlled subprocess results. | References and process controls. Hosted acceptance not executed. |

## Interpretation

For each hosted stage, `passed / attempted` is 0/0 (Not measured). The skipped stage jobs are not treated as attempts or successes. In the one historical end-to-end **fixture**, Requirements, Design, Release and Review each pass 1/1 mock-flow stage attempt. Implementation compiles 2/2 and Testing passes 1/2 over two actual local source attempts. The fixture’s [MERGE_READINESS_CHECK](local-validation/fixture-artifacts/MERGE_READINESS_CHECK.json) says `automated_gates_satisfied=false`, `human_decision=pending`, `merge_authorized=false`. No hosted readiness or model review accuracy is established.

Separate model-assisted security reviews found unsafe verdict provenance and non-atomic provider authorization, followed by dispatch and check-issuer gaps. These are engineering reviews, separate from the assignment evaluator. Its true/false positives and misses were not measured. The local fixture’s synthetic approval cannot assess reviewer accuracy. Paid hosted model use was not observed and total coordinator usage is not measured. Provider secret availability and an enforced account hard cap remain unverified.
